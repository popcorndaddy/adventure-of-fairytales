package com.popcorndaddy.gatekeeper.entity;

import com.popcorndaddy.gatekeeper.GatekeeperMod;
import com.popcorndaddy.gatekeeper.portal.PortalData;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtUtils;
import net.minecraft.network.chat.Component;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerBossEvent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.util.Mth;
import net.minecraft.world.BossEvent;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageTypes;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

import javax.annotation.Nullable;
import java.util.List;

/**
 * The Ancient Gatekeeper. Sleeps (dormant, invulnerable) in front of a portal until a player comes close,
 * then awakens (cinematic: arms unfold, head turns, sword drag, eyes ignite), steps forward and fights:
 * overhead smash, horizontal sweep, multi-arm combo, blocks projectiles, staggers on heavy hits, enrages at half health.
 * All timings are the Blender clips' frames converted from 30 fps to 20 ticks per second.
 */
public class GatekeeperEntity extends Monster implements GeoEntity {
    public static final int PHASE_DORMANT = 0, PHASE_AWAKENING = 1, PHASE_FIGHT = 2;
    private static final int AWAKENING_TICKS = 120, ENTRANCE_TICKS = 67;

    private static final EntityDataAccessor<Integer> PHASE = SynchedEntityData.defineId(GatekeeperEntity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> AWAKE_TICKS = SynchedEntityData.defineId(GatekeeperEntity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Boolean> EYES_OPEN = SynchedEntityData.defineId(GatekeeperEntity.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Boolean> ENRAGED = SynchedEntityData.defineId(GatekeeperEntity.class, EntityDataSerializers.BOOLEAN);

    private static final RawAnimation DORMANT = RawAnimation.begin().thenLoop("animation.gatekeeper.dormant");
    private static final RawAnimation AWAKENING = RawAnimation.begin().thenPlay("animation.gatekeeper.awakening");
    private static final RawAnimation ENTRANCE = RawAnimation.begin().thenPlay("animation.gatekeeper.entrance");
    private static final RawAnimation IDLE = RawAnimation.begin().thenLoop("animation.gatekeeper.idle");
    private static final RawAnimation WALKING = RawAnimation.begin().thenLoop("animation.gatekeeper.walking");
    private static final RawAnimation HEAVY_WALK = RawAnimation.begin().thenLoop("animation.gatekeeper.heavy_walk");
    private static final RawAnimation SWORD_DRAG = RawAnimation.begin().thenLoop("animation.gatekeeper.sword_drag");

    private enum Action {
        NONE("", 0), OVERHEAD("overhead", 48), SWEEP("sweep", 44), MULTI("multi", 73),
        BLOCK("block", 29), STAGGER("stagger", 32), RAGE("rage", 67), GRAVITY_WELL("gravity_well", 100);
        final String anim; final int length;
        Action(String anim, int length) { this.anim = anim; this.length = length; }
    }

    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);
    private final ServerBossEvent bossEvent = new ServerBossEvent(Component.translatable("entity.aof_gatekeeper.gatekeeper"),
            BossEvent.BossBarColor.PURPLE, BossEvent.BossBarOverlay.NOTCHED_10);
    private Action action = Action.NONE;
    private int actionTicks, attackCooldown = 40, staggerCooldown, blockCooldown, gravityCooldown = 160;

    /** Gravity well timings (ticks): the sword is planted and the pull starts, then the burst. */
    public static final int GW_OPEN = 16, GW_BURST = 76;
    public static final double GW_RADIUS = 16.0, GW_BURST_RADIUS = 7.5;
    private boolean rageDone;
    @Nullable private BlockPos guardedPortal;

    public GatekeeperEntity(EntityType<? extends Monster> type, Level level) {
        super(type, level);
        this.xpReward = 400;
        this.setPersistenceRequired();
        this.bossEvent.setVisible(false);
        this.setMaxUpStep(1.5f);
    }

    public static AttributeSupplier.Builder createAttributes() {
        return Monster.createMonsterAttributes()
                .add(Attributes.MAX_HEALTH, 1200.0)
                .add(Attributes.ARMOR, 18.0)
                .add(Attributes.ARMOR_TOUGHNESS, 8.0)
                .add(Attributes.ATTACK_DAMAGE, 24.0)
                .add(Attributes.MOVEMENT_SPEED, 0.24)
                .add(Attributes.KNOCKBACK_RESISTANCE, 1.0)
                .add(Attributes.FOLLOW_RANGE, 48.0);
    }

    @Override
    protected void defineSynchedData() {
        super.defineSynchedData();
        this.entityData.define(PHASE, PHASE_DORMANT);
        this.entityData.define(AWAKE_TICKS, 0);
        this.entityData.define(EYES_OPEN, false);
        this.entityData.define(ENRAGED, false);
    }

    @Override
    protected void registerGoals() {
        this.targetSelector.addGoal(1, new HurtByTargetGoal(this));
        this.targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, 10, true, false, p -> !((Player) p).isCreative() && !p.isSpectator()));
    }

    // ---------------------------------------------------------------- state accessors
    public int phase() { return this.entityData.get(PHASE); }
    public int awakeTicks() { return this.entityData.get(AWAKE_TICKS); }
    public boolean eyesOpen() { return this.entityData.get(EYES_OPEN); }
    public boolean enraged() { return this.entityData.get(ENRAGED); }
    public void setGuardedPortal(@Nullable BlockPos pos) { this.guardedPortal = pos; }
    @Nullable public BlockPos guardedPortal() { return this.guardedPortal; }

    /** Rooted in place (dormant, awakening, or mid-attack). Not isImmobile(): that would also skip the AI tick. */
    private boolean rooted() {
        return this.phase() == PHASE_DORMANT || (this.phase() == PHASE_AWAKENING && !this.entranceStepping())
                || this.action != Action.NONE || this.isDeadOrDying();
    }

    private void holdStill() {
        this.getNavigation().stop();
        this.setXxa(0); this.setZza(0); this.setSpeed(0);
        Vec3 v = this.getDeltaMovement();
        this.setDeltaMovement(0, v.y, 0);
    }

    private boolean entranceStepping() {
        int t = this.awakeTicks() - AWAKENING_TICKS;
        return t >= 20 && t <= 50;
    }

    @Override public boolean removeWhenFarAway(double d) { return false; }
    @Override public boolean isPushable() { return false; }
    @Override public boolean canBeLeashed(Player p) { return false; }
    @Override protected boolean canRide(net.minecraft.world.entity.Entity e) { return false; }

    // ---------------------------------------------------------------- damage
    @Override
    public boolean isInvulnerableTo(DamageSource source) {
        return source.is(DamageTypes.IN_WALL) || source.is(DamageTypes.FALL) || source.is(DamageTypes.DROWN) || super.isInvulnerableTo(source);
    }

    @Override
    public boolean hurt(DamageSource source, float amount) {
        boolean bypass = source.is(DamageTypeTags.BYPASSES_INVULNERABILITY);
        if (!bypass && (this.phase() != PHASE_FIGHT || this.action == Action.RAGE)) {
            if (!this.level().isClientSide && this.phase() == PHASE_DORMANT && source.getEntity() instanceof Player p && !p.isCreative()) {
                this.startAwakening();                       // striking the sleeping guardian wakes him
            }
            return false;
        }
        if (!this.level().isClientSide && !bypass) {
            if (source.getDirectEntity() instanceof Projectile && this.action == Action.NONE && this.blockCooldown <= 0 && this.random.nextFloat() < 0.4f) {
                this.startAction(Action.BLOCK);
                this.blockCooldown = 140;
            }
            if (this.action == Action.BLOCK) {
                amount *= 0.15f;
                this.playSound(GatekeeperMod.SND_IMPACT.get(), 0.6f, 1.6f);
            }
        }
        boolean result = super.hurt(source, amount);
        if (result && !this.level().isClientSide && !bypass && amount >= 30f && this.staggerCooldown <= 0
                && this.action != Action.RAGE && this.action != Action.BLOCK && this.isAlive()) {
            this.startAction(Action.STAGGER);
            this.staggerCooldown = 220;
        }
        return result;
    }

    @Override
    public void die(DamageSource source) {
        super.die(source);
        if (!this.level().isClientSide) {
            this.action = Action.NONE;
            this.triggerAnim("main", "death");
            this.playSound(GatekeeperMod.SND_SHRIEK.get(), 4.0f, 0.6f);
            if (this.guardedPortal != null && this.level() instanceof ServerLevel sl) {
                PortalData.get(sl).markDefeated(this.guardedPortal);
                for (ServerPlayer p : sl.players()) {
                    if (p.distanceToSqr(this) < 96 * 96) {
                        p.displayClientMessage(Component.translatable("message.aof_gatekeeper.seal_broken"), false);
                    }
                }
            }
        }
    }

    @Override
    protected void tickDeath() {
        ++this.deathTime;
        if (this.level() instanceof ServerLevel sl && this.deathTime % 4 == 0) {
            sl.sendParticles(ParticleTypes.REVERSE_PORTAL, this.getX(), this.getY() + 2.5, this.getZ(), 30, 1.5, 2.0, 1.5, 0.05);
        }
        if (this.deathTime == 66) {
            this.burst(ParticleTypes.EXPLOSION, this.position(), 4, 1.5);
            this.playSound(GatekeeperMod.SND_IMPACT.get(), 3.0f, 0.7f);
        }
        if (this.deathTime >= 87 && !this.level().isClientSide && !this.isRemoved()) {
            this.level().broadcastEntityEvent(this, (byte) 60);
            this.remove(RemovalReason.KILLED);
        }
    }

    // ---------------------------------------------------------------- boss bar
    @Override
    public void startSeenByPlayer(ServerPlayer player) {
        super.startSeenByPlayer(player);
        this.bossEvent.addPlayer(player);
    }

    @Override
    public void stopSeenByPlayer(ServerPlayer player) {
        super.stopSeenByPlayer(player);
        this.bossEvent.removePlayer(player);
    }

    // ---------------------------------------------------------------- main server logic
    public void startAwakening() {
        if (this.phase() != PHASE_DORMANT) return;
        this.entityData.set(PHASE, PHASE_AWAKENING);
        this.entityData.set(AWAKE_TICKS, 0);
        this.playSound(GatekeeperMod.SND_PORTAL.get(), 3.0f, 1.0f);
    }

    @Override
    protected void customServerAiStep() {
        super.customServerAiStep();
        this.bossEvent.setVisible(this.phase() != PHASE_DORMANT);
        this.bossEvent.setProgress(this.getHealth() / this.getMaxHealth());
        if (this.staggerCooldown > 0) this.staggerCooldown--;
        if (this.blockCooldown > 0) this.blockCooldown--;
        if (this.gravityCooldown > 0 && this.action == Action.NONE) this.gravityCooldown--;

        switch (this.phase()) {
            case PHASE_DORMANT -> this.tickDormant();
            case PHASE_AWAKENING -> this.tickAwakening();
            default -> this.tickFight();
        }
        if (this.rooted()) this.holdStill();
    }

    private void tickDormant() {
        this.getNavigation().stop();
        if (this.tickCount % 10 == 0) {
            Player p = this.level().getNearestPlayer(this, 20.0);
            if (p != null && !p.isCreative() && !p.isSpectator() && this.hasLineOfSight(p)) {
                this.setTarget(p);
                this.startAwakening();
            }
        }
        if (this.tickCount % 40 == 0 && this.level() instanceof ServerLevel sl) {
            sl.sendParticles(ParticleTypes.PORTAL, this.getX(), this.getY() + 2, this.getZ(), 12, 1.2, 1.5, 1.2, 0.2);
        }
    }

    private void tickAwakening() {
        int t = this.awakeTicks() + 1;
        this.entityData.set(AWAKE_TICKS, t);
        LivingEntity target = this.getTarget();
        if (t > 67 && target != null) this.faceTarget(target, 6f);                 // head turns toward the player
        switch (t) {
            case 29, 41 -> this.playSound(GatekeeperMod.SND_PULSE.get(), 2.5f, 1.0f); // additional arms unfold, fire ignites
            case 73 -> this.playSound(GatekeeperMod.SND_DRAG.get(), 2.5f, 1.0f);      // the blade scrapes the stone
            case 75 -> this.playSound(GatekeeperMod.SND_EYES.get(), 3.0f, 1.0f);
            case 107 -> this.entityData.set(EYES_OPEN, true);                         // the eyes open
            default -> { }
        }
        if (t >= 73 && t <= 100 && t % 2 == 0) {
            this.burst(ParticleTypes.ELECTRIC_SPARK, this.localPoint(-2.6, 0.2, -1.8), 6, 0.3);
            this.burst(ParticleTypes.REVERSE_PORTAL, this.localPoint(-2.6, 0.2, -1.8), 3, 0.3);
        }
        int e = t - AWAKENING_TICKS;                                                  // entrance: one heavy step that blocks the gate
        if (e >= 20 && e <= 50) {
            Vec3 fwd = Vec3.directionFromRotation(0, this.getYRot()).scale(0.05);
            this.setDeltaMovement(fwd.x, this.getDeltaMovement().y, fwd.z);
        }
        if (e == 27 || e == 49) this.stomp(this.localPoint(e == 27 ? 0.8 : -0.8, 0, 0.5), 2.8, 0, 0.6f);
        if (e == 43) this.playSound(GatekeeperMod.SND_SHRIEK.get(), 4.0f, 0.8f);
        if (e >= ENTRANCE_TICKS) {
            this.entityData.set(PHASE, PHASE_FIGHT);
            this.attackCooldown = 20;
        }
    }

    private void tickFight() {
        LivingEntity target = this.getTarget();
        if (!this.rageDone && this.getHealth() <= this.getMaxHealth() * 0.5f && this.action == Action.NONE) {
            this.rageDone = true;
            this.startAction(Action.RAGE);
        }
        if (this.action != Action.NONE) {
            this.getNavigation().stop();
            this.tickAction(target);
            return;
        }
        if (this.attackCooldown > 0) this.attackCooldown--;
        if (target == null || !target.isAlive()) {
            if (this.tickCount % 200 == 0) this.playSound(GatekeeperMod.SND_AMBIENT.get(), 2.0f, 1.0f);
            return;
        }
        double dist = Math.sqrt(this.distanceToSqr(target));
        this.getLookControl().setLookAt(target, 20f, 20f);
        if (dist > 5.0 || this.attackCooldown > 0) {
            double speed = dist > 14 ? 1.35 : 1.0;
            this.getNavigation().moveTo(target, this.enraged() ? speed * 1.2 : speed);
        } else {
            this.getNavigation().stop();
        }
        if (this.attackCooldown <= 0 && this.gravityCooldown <= 0 && dist > 6.5 && dist <= GW_RADIUS - 2 && this.hasLineOfSight(target)) {
            this.faceTarget(target, 360f);                 // out of sword reach: drag them in
            this.startAction(Action.GRAVITY_WELL);
            this.gravityCooldown = this.enraged() ? 260 : 380;
            return;
        }
        if (this.attackCooldown <= 0 && dist <= 7.0 && this.hasLineOfSight(target)) {
            float r = this.random.nextFloat();
            Action a = dist > 5.5 ? (r < 0.6f ? Action.SWEEP : Action.OVERHEAD)
                    : (r < 0.38f ? Action.OVERHEAD : r < 0.72f ? Action.SWEEP : Action.MULTI);
            this.faceTarget(target, 360f);
            this.startAction(a);
        }
        if (this.tickCount % 12 == 0 && this.getDeltaMovement().horizontalDistanceSqr() > 0.002) {
            this.playSound(GatekeeperMod.SND_STEP.get(), 1.4f, 0.9f + this.random.nextFloat() * 0.2f);
            this.burst(ParticleTypes.CAMPFIRE_COSY_SMOKE, this.position(), 2, 0.6);
        }
    }

    private void startAction(Action a) {
        this.action = a;
        this.actionTicks = 0;
        this.triggerAnim("main", a.anim);
    }

    private void tickAction(@Nullable LivingEntity target) {
        int t = ++this.actionTicks;
        float dmg = (float) this.getAttributeValue(Attributes.ATTACK_DAMAGE) * (this.enraged() ? 1.2f : 1.0f);
        boolean tracking = target != null && target.isAlive();
        switch (this.action) {
            case OVERHEAD -> {
                if (tracking && t < 20) this.faceTarget(target, 8f);
                if (t == 14) this.playSound(GatekeeperMod.SND_WHOOSH.get(), 2.0f, 0.7f);
                if (t == 23) {
                    Vec3 hit = this.localPoint(0.2, 0, 4.0);
                    this.stomp(hit, 3.2, dmg * 1.4f, 1.6f);
                    this.burst(ParticleTypes.EXPLOSION, hit, 3, 1.0);
                    this.burst(ParticleTypes.REVERSE_PORTAL, hit, 60, 1.5);
                }
            }
            case SWEEP -> {
                if (tracking && t < 10) this.faceTarget(target, 10f);
                if (t == 11) this.playSound(GatekeeperMod.SND_WHOOSH.get(), 2.2f, 0.8f);
                if (t == 16) {
                    this.arcHit(6.5, 115, dmg, 1.8f);
                    this.shockwave(6.5);
                    this.playSound(GatekeeperMod.SND_IMPACT.get(), 1.6f, 1.1f);
                }
            }
            case MULTI -> {
                if (tracking && t < 40) this.faceTarget(target, 6f);
                if (t == 8) this.pointHit(this.localPoint(-1.8, 2.5, 3.4), 2.4, dmg * 0.55f, 0.8f);     // right claw
                if (t == 16) this.pointHit(this.localPoint(1.8, 2.5, 3.4), 2.4, dmg * 0.55f, 0.8f);     // left claw
                if (t == 20) this.pointHit(this.localPoint(1.0, 1.6, 3.8), 2.2, dmg * 0.75f, 1.4f);     // rune fist
                if (t == 41) { this.arcHit(6.0, 100, dmg * 0.85f, 1.5f); this.shockwave(5.5); }        // sword finisher
                if (t == 6 || t == 14 || t == 19 || t == 37) this.playSound(GatekeeperMod.SND_WHOOSH.get(), 1.6f, 1.0f);
            }
            case RAGE -> {
                if (t == 19) {
                    this.playSound(GatekeeperMod.SND_SHRIEK.get(), 5.0f, 0.7f);
                    this.entityData.set(ENRAGED, true);
                    this.shockwave(8.0);
                    for (LivingEntity e : this.nearby(this.position(), 8.0)) {
                        Vec3 push = e.position().subtract(this.position()).normalize().scale(1.6);
                        e.push(push.x, 0.5, push.z);
                    }
                }
                if (t > 19 && t % 4 == 0) this.burst(ParticleTypes.DRAGON_BREATH, this.position().add(0, 3, 0), 20, 2.0);
            }
            case GRAVITY_WELL -> this.tickGravityWell(t, target, dmg);
            default -> { }
        }
        if (t >= this.action.length) {
            int base = this.enraged() ? 22 : 34;
            this.attackCooldown = switch (this.action) {
                case OVERHEAD, MULTI -> base + 10;
                case SWEEP -> base;
                default -> 10;
            };
            this.action = Action.NONE;
        }
    }

    // ---------------------------------------------------------------- gravity well
    /**
     * He plants the sword (tick 16) and opens a well: for 3 seconds everything within 16 blocks is dragged toward him
     * on an inward spiral (stronger the closer it gets), crushed a little at the core; on tick 76 it bursts and flings
     * everything near him outward. A heavy hit (stagger) during the channel breaks it.
     */
    private void tickGravityWell(int t, @Nullable LivingEntity target, float dmg) {
        if (t < GW_OPEN && target != null && target.isAlive()) this.faceTarget(target, 8f);
        if (t == 6) this.playSound(GatekeeperMod.SND_WHOOSH.get(), 2.0f, 0.6f);
        if (t == GW_OPEN) {
            Vec3 tip = this.localPoint(0.2, 0, 1.4);
            this.playSound(GatekeeperMod.SND_IMPACT.get(), 2.5f, 0.6f);
            this.playSound(GatekeeperMod.SND_PORTAL.get(), 3.0f, 0.7f);
            this.burst(ParticleTypes.REVERSE_PORTAL, tip, 40, 0.6);
            this.burst(ParticleTypes.CAMPFIRE_COSY_SMOKE, tip, 8, 0.6);
        }
        if (t >= GW_OPEN && t < GW_BURST) {
            float ramp = Math.min(1f, (t - GW_OPEN) / 10f) * (t >= GW_BURST - 10 ? 1.35f : 1f);
            Vec3 c = this.position();
            for (LivingEntity e : this.nearby(c, GW_RADIUS)) {
                Vec3 d = new Vec3(c.x - e.getX(), 0, c.z - e.getZ());
                double dist = d.length();
                if (dist > GW_RADIUS || dist < 1e-3) continue;
                Vec3 in = d.scale(1 / dist);
                Vec3 swirl = new Vec3(-in.z, 0, in.x);                                   // counter-clockwise around him
                double s = (0.045 + 0.075 * (1 - dist / GW_RADIUS)) * ramp;
                Vec3 pull = dist < 2.4 ? swirl.scale(s * 0.5) : in.scale(s).add(swirl.scale(s * 0.45));
                Vec3 v = e.getDeltaMovement().add(pull);
                e.setDeltaMovement(v.x, Math.min(v.y, 0.25), v.z);
                e.hurtMarked = true;                                                       // players: send the new velocity
                e.fallDistance = 0;
                if (dist < 3.5 && t % 20 == 0) e.hurt(this.damageSources().indirectMagic(this, this), 2.0f);
            }
            if (t % 2 == 0) this.gravityWellParticles(t);
            if ((t - GW_OPEN) % 20 == 0) this.playSound(GatekeeperMod.SND_PULSE.get(), 2.5f, 0.6f + 0.15f * (t - GW_OPEN) / 20f);
        }
        if (t == GW_BURST) {
            for (LivingEntity e : this.nearby(this.position(), GW_BURST_RADIUS)) {
                Vec3 d = new Vec3(e.getX() - this.getX(), 0, e.getZ() - this.getZ());
                Vec3 out = d.lengthSqr() < 1e-4 ? Vec3.directionFromRotation(0, this.yBodyRot) : d.normalize();
                e.hurt(this.damageSources().mobAttack(this), dmg * 0.9f);
                e.setDeltaMovement(out.x * 2.2, 0.65, out.z * 2.2);
                e.hurtMarked = true;
            }
            this.shockwave(GW_BURST_RADIUS + 1.5);
            this.burst(ParticleTypes.EXPLOSION_EMITTER, this.position().add(0, 2.5, 0), 1, 0);
            this.burst(ParticleTypes.REVERSE_PORTAL, this.position().add(0, 3, 0), 120, 2.5);
            this.burst(ParticleTypes.DRAGON_BREATH, this.position().add(0, 1, 0), 60, 3.0);
            this.playSound(GatekeeperMod.SND_IMPACT.get(), 4.0f, 0.5f);
            this.playSound(GatekeeperMod.SND_SHRIEK.get(), 3.5f, 0.9f);
        }
    }

    /** Three spiral arms of particles winding into him, turning faster as the well tightens, plus rising motes at the core. */
    private void gravityWellParticles(int t) {
        if (!(this.level() instanceof ServerLevel sl)) return;
        double spin = 0.06 * t + 0.0012 * t * t;
        for (int arm = 0; arm < 3; arm++) {
            for (int i = 0; i < 9; i++) {
                double u = i / 8.0;
                double r = 1.5 + (GW_RADIUS - 3) * Math.pow(1 - u, 1.25);
                double a = spin + arm * (Math.PI * 2 / 3) + u * Math.PI * 2 * 1.4;
                double x = this.getX() + Math.cos(a) * r, z = this.getZ() + Math.sin(a) * r;
                sl.sendParticles(i % 3 == 0 ? ParticleTypes.REVERSE_PORTAL : ParticleTypes.PORTAL, x, this.getY() + 0.15, z, 1, 0.05, 0.02, 0.05, 0);
            }
        }
        sl.sendParticles(ParticleTypes.REVERSE_PORTAL, this.getX(), this.getY() + 3.5, this.getZ(), 6, 1.6, 1.2, 1.6, 0.02);
        if (t % 6 == 0) sl.sendParticles(ParticleTypes.DRAGON_BREATH, this.getX(), this.getY() + 0.4, this.getZ(), 10, 2.5, 0.1, 2.5, 0.01);
    }

    /** True while the gravity well is channelling or bursting (for tests and other systems). */
    public boolean usingGravityWell() { return this.action == Action.GRAVITY_WELL; }

    /** Start the gravity well now (if he is fighting and not mid-action). Used by tests and commands. */
    public boolean forceGravityWell() {
        if (this.phase() != PHASE_FIGHT || this.action != Action.NONE || this.isDeadOrDying()) return false;
        this.startAction(Action.GRAVITY_WELL);
        return true;
    }

    // ---------------------------------------------------------------- combat helpers
    /** A point in the boss's local frame (x = his left, z = forward), in world space. */
    private Vec3 localPoint(double right, double up, double forward) {
        float yaw = this.yBodyRot * Mth.DEG_TO_RAD;
        double fx = -Mth.sin(yaw), fz = Mth.cos(yaw);
        return new Vec3(this.getX() + fx * forward + fz * right, this.getY() + up, this.getZ() + fz * forward - fx * right);
    }

    private void faceTarget(LivingEntity target, float maxTurn) {
        double dx = target.getX() - this.getX(), dz = target.getZ() - this.getZ();
        float want = (float) (Mth.atan2(dz, dx) * Mth.RAD_TO_DEG) - 90f;
        float yaw = Mth.approachDegrees(this.getYRot(), want, maxTurn);
        this.setYRot(yaw); this.yBodyRot = yaw; this.yHeadRot = yaw;
    }

    private List<LivingEntity> nearby(Vec3 c, double r) {
        return this.level().getEntitiesOfClass(LivingEntity.class, new AABB(c, c).inflate(r, 4, r),
                e -> e != this && e.isAlive() && !(e instanceof GatekeeperEntity) && e.distanceToSqr(c) <= r * r + 16);
    }

    private void pointHit(Vec3 c, double r, float dmg, float knock) {
        for (LivingEntity e : this.nearby(c, r)) {
            if (e.hurt(this.damageSources().mobAttack(this), dmg)) {
                Vec3 d = e.position().subtract(this.position()).normalize();
                e.knockback(knock, -d.x, -d.z);
            }
        }
        this.burst(ParticleTypes.CRIT, c, 12, 0.6);
    }

    private void arcHit(double r, double halfAngle, float dmg, float knock) {
        Vec3 look = Vec3.directionFromRotation(0, this.yBodyRot);
        for (LivingEntity e : this.nearby(this.position(), r)) {
            Vec3 d = e.position().subtract(this.position());
            Vec3 flat = new Vec3(d.x, 0, d.z);
            if (flat.lengthSqr() < 0.01) continue;
            double ang = Math.toDegrees(Math.acos(Mth.clamp(flat.normalize().dot(look), -1, 1)));
            if (ang <= halfAngle && e.hurt(this.damageSources().mobAttack(this), dmg)) {
                e.knockback(knock, -flat.normalize().x, -flat.normalize().z);
            }
        }
    }

    /** Ground impact: damage + knock-up in a radius, dust and a sound. */
    private void stomp(Vec3 c, double r, float dmg, float knock) {
        if (dmg > 0) {
            for (LivingEntity e : this.nearby(c, r)) {
                if (e.hurt(this.damageSources().mobAttack(this), dmg)) {
                    Vec3 d = e.position().subtract(c);
                    e.knockback(knock, -d.x, -d.z);
                    e.push(0, 0.45, 0);
                }
            }
        }
        this.burst(ParticleTypes.CAMPFIRE_COSY_SMOKE, c, 12, r * 0.5);
        this.burst(ParticleTypes.REVERSE_PORTAL, c, 30, r * 0.5);
        this.playSound(GatekeeperMod.SND_STEP.get(), 2.5f, 0.8f);
        if (dmg > 0) this.playSound(GatekeeperMod.SND_IMPACT.get(), 3.0f, 0.9f);
    }

    private void shockwave(double r) {
        if (!(this.level() instanceof ServerLevel sl)) return;
        for (int i = 0; i < 48; i++) {
            double a = Math.PI * 2 * i / 48;
            sl.sendParticles(ParticleTypes.REVERSE_PORTAL, this.getX() + Math.cos(a) * r, this.getY() + 0.2, this.getZ() + Math.sin(a) * r, 2, 0.1, 0.05, 0.1, 0.02);
            sl.sendParticles(ParticleTypes.SWEEP_ATTACK, this.getX() + Math.cos(a) * r * 0.7, this.getY() + 0.6, this.getZ() + Math.sin(a) * r * 0.7, 1, 0, 0, 0, 0);
        }
    }

    private void burst(ParticleOptions type, Vec3 c, int count, double spread) {
        if (this.level() instanceof ServerLevel sl) {
            sl.sendParticles(type, c.x, c.y, c.z, count, spread, spread * 0.5, spread, 0.05);
        }
    }

    @Override
    public void playSound(SoundEvent sound, float volume, float pitch) {
        this.level().playSound(null, this.getX(), this.getY(), this.getZ(), sound, SoundSource.HOSTILE, volume, pitch);
    }

    @Override protected SoundEvent getAmbientSound() { return this.phase() == PHASE_FIGHT ? GatekeeperMod.SND_AMBIENT.get() : null; }
    @Override public int getAmbientSoundInterval() { return 240; }
    @Override protected SoundEvent getHurtSound(DamageSource s) { return GatekeeperMod.SND_PULSE.get(); }
    @Override protected SoundEvent getDeathSound() { return null; }
    @Override protected float getSoundVolume() { return 2.0f; }

    // ---------------------------------------------------------------- save / load
    @Override
    public void addAdditionalSaveData(CompoundTag tag) {
        super.addAdditionalSaveData(tag);
        tag.putInt("GkPhase", this.phase());
        tag.putBoolean("GkRageDone", this.rageDone);
        tag.putBoolean("GkEnraged", this.enraged());
        if (this.guardedPortal != null) tag.put("GkPortal", NbtUtils.writeBlockPos(this.guardedPortal));
    }

    @Override
    public void readAdditionalSaveData(CompoundTag tag) {
        super.readAdditionalSaveData(tag);
        int ph = tag.getInt("GkPhase");
        this.entityData.set(PHASE, ph == PHASE_AWAKENING ? PHASE_FIGHT : ph);    // an interrupted awakening resumes as a fight
        this.entityData.set(EYES_OPEN, ph != PHASE_DORMANT);
        this.rageDone = tag.getBoolean("GkRageDone");
        this.entityData.set(ENRAGED, tag.getBoolean("GkEnraged"));
        if (tag.contains("GkPortal")) this.guardedPortal = NbtUtils.readBlockPos(tag.getCompound("GkPortal"));
    }

    /**
     * He is always "The Ancient Gatekeeper". Some pack mods (e.g. Villager Names) give random names to mobs as they
     * spawn, which would rename his boss bar and death messages, so custom names are ignored.
     */
    @Override
    public void setCustomName(@Nullable Component name) {
        super.setCustomName(null);
        this.bossEvent.setName(Component.translatable("entity.aof_gatekeeper.gatekeeper"));
    }

    @Override @Nullable public Component getCustomName() { return null; }
    @Override public boolean hasCustomName() { return false; }

    // ---------------------------------------------------------------- GeckoLib
    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
        controllers.add(new AnimationController<>(this, "main", 6, state -> {
            if (this.phase() == PHASE_DORMANT) return state.setAndContinue(DORMANT);
            if (this.phase() == PHASE_AWAKENING) return state.setAndContinue(this.awakeTicks() < AWAKENING_TICKS ? AWAKENING : ENTRANCE);
            if (state.isMoving()) {
                if (this.enraged()) return state.setAndContinue(SWORD_DRAG);
                return state.setAndContinue(this.getDeltaMovement().horizontalDistanceSqr() > 0.012 ? WALKING : HEAVY_WALK);
            }
            return state.setAndContinue(IDLE);
        })
                .triggerableAnim("overhead", RawAnimation.begin().thenPlay("animation.gatekeeper.overhead_attack"))
                .triggerableAnim("sweep", RawAnimation.begin().thenPlay("animation.gatekeeper.horizontal_sweep"))
                .triggerableAnim("multi", RawAnimation.begin().thenPlay("animation.gatekeeper.multi_arm_attack"))
                .triggerableAnim("block", RawAnimation.begin().thenPlay("animation.gatekeeper.block"))
                .triggerableAnim("stagger", RawAnimation.begin().thenPlay("animation.gatekeeper.stagger"))
                .triggerableAnim("rage", RawAnimation.begin().thenPlay("animation.gatekeeper.rage"))
                .triggerableAnim("gravity_well", RawAnimation.begin().thenPlay("animation.gatekeeper.gravity_well"))
                .triggerableAnim("death", RawAnimation.begin().thenPlayAndHold("animation.gatekeeper.death")));
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return this.cache;
    }

    /** Spawn a dormant guardian at `pos`, facing `facePos`, guarding `portal`. */
    public static GatekeeperEntity spawnGuardian(ServerLevel level, BlockPos pos, Vec3 facePos, @Nullable BlockPos portal) {
        GatekeeperEntity g = GatekeeperMod.GATEKEEPER.get().create(level);
        if (g == null) return null;
        double dx = facePos.x - (pos.getX() + 0.5), dz = facePos.z - (pos.getZ() + 0.5);
        float yaw = (float) (Mth.atan2(dz, dx) * Mth.RAD_TO_DEG) - 90f;
        g.moveTo(pos.getX() + 0.5, pos.getY(), pos.getZ() + 0.5, yaw, 0);
        g.yBodyRot = yaw; g.yHeadRot = yaw;
        g.setGuardedPortal(portal);
        level.addFreshEntity(g);
        return g;
    }

    @Override
    public boolean checkSpawnRules(net.minecraft.world.level.LevelAccessor level, net.minecraft.world.entity.MobSpawnType reason) {
        return true;
    }

    @Override
    public boolean isPersistenceRequired() {
        return true;
    }

    @SuppressWarnings("unused")
    private static boolean isBoss(Mob m) { return m instanceof GatekeeperEntity; }
}
