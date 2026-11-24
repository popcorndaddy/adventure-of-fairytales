package com.aof.gateknight.entity;

import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.BlockParticleOption;
import net.minecraft.core.particles.ParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtUtils;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerBossEvent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.util.Mth;
import net.minecraft.world.BossEvent;
import net.minecraft.world.DifficultyInstance;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;
import net.minecraft.world.damagesource.DamageTypes;
import net.minecraft.world.effect.MobEffectCategory;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.monster.WitherSkeleton;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.ProjectileWeaponItem;
import net.minecraft.world.item.TridentItem;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.registries.ForgeRegistries;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.util.GeckoLibUtil;

import javax.annotation.Nullable;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.UUID;

/**
 * The Gate Knight: an ancient dark knight, ~8.4 blocks tall, 600 HP.
 *
 * Moves (ticks match gate_knight.animation.json at 20 ticks/s):
 *   sweep      low cut across his front, reaches ~5.5 blocks
 *   stomp      foot slam: the ground heaves up in rings, everything within 6 blocks takes ~6 damage
 *   dash       charges ~10 blocks at the target behind a two-handed thrust
 *   shockwave  open palm: a wave throws whoever is in front of him 5-6 blocks back
 *   block      raises the sword to stop arrows and other projectiles from the front
 * At half health he kneels on one knee (invincible) while 9 wither skeletons rise around him; when every one is dead
 * he stands, roars and burns brighter (faster, harder hitting, shorter cooldowns). Magic barely scratches him.
 */
public class GateKnightEntity extends Monster implements GeoEntity {
    // ---------------------------------------------------------------- tuning
    public static final double SPEED = 0.30, SPEED_ENRAGED = 0.34;
    static final int SWEEP_LEN = 28, SWEEP_HIT = 13, SWEEP_CD = 40;      static final double SWEEP_REACH = 5.5, SWEEP_ARC = 70; static final float SWEEP_DMG = 16f;
    static final int STOMP_LEN = 32, STOMP_HIT = 16, STOMP_CD = 140;     static final double STOMP_RADIUS = 6.0;                static final float STOMP_DMG = 6f;
    static final int DASH_LEN = 26, DASH_GO = 7, DASH_STOP = 16, DASH_CD = 160; static final double DASH_SPEED = 1.15, DASH_MIN = 6, DASH_MAX = 16; static final float DASH_DMG = 18f;
    static final int WAVE_LEN = 28, WAVE_HIT = 11, WAVE_CD = 200;        static final double WAVE_REACH = 8, WAVE_ARC = 55, WAVE_PUSH = 1.15; static final float WAVE_DMG = 4f;
    static final int BLOCK_LEN = 36, BLOCK_SHORT = 24, BLOCK_CD = 120;
    static final int KNEEL_SUMMON = 30, MINIONS = 9;
    static final int ROAR_LEN = 52, ROAR_GLOW = 24;
    static final int GAP = 14;
    public static final float MAGIC_TAKEN = 0.15f;

    public static final int PHASE_FIGHT = 0, PHASE_KNEEL = 1, PHASE_ENRAGED = 2;

    public enum Action {
        NONE(""), SWEEP("sweep"), STOMP("stomp"), DASH("dash"), WAVE("shockwave"), BLOCK("block"), KNEEL("kneel"), ROAR("roar");
        public final String anim;
        Action(String anim) { this.anim = anim; }
    }

    private static final EntityDataAccessor<Integer> PHASE = SynchedEntityData.defineId(GateKnightEntity.class, EntityDataSerializers.INT);

    private static final RawAnimation IDLE = RawAnimation.begin().thenLoop("idle");
    private static final RawAnimation WALK = RawAnimation.begin().thenLoop("walk");
    private static final RawAnimation KNEEL_HOLD = RawAnimation.begin().thenPlayAndHold("kneel");

    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);
    private final ServerBossEvent bossEvent = new ServerBossEvent(Component.translatable("entity.aof_gateknight.gate_knight"),
            BossEvent.BossBarColor.PURPLE, BossEvent.BossBarOverlay.NOTCHED_10);

    private Action action = Action.NONE;
    private int actionTicks, actionLength, gap = 20;
    private int cdSweep, cdStomp, cdDash, cdWave, cdBlock;
    private float dashYaw;
    private final List<UUID> dashHit = new ArrayList<>();
    private final List<UUID> minions = new ArrayList<>();
    private final List<Pending> pending = new ArrayList<>();
    private int minionsSpawnedAt = -1;

    private record Pending(int at, Runnable run) {}

    public GateKnightEntity(EntityType<? extends Monster> type, Level level) {
        super(type, level);
        this.xpReward = 500;
        this.setPersistenceRequired();
        this.setMaxUpStep(1.6f);
    }

    public static AttributeSupplier.Builder createAttributes() {
        return Monster.createMonsterAttributes()
                .add(Attributes.MAX_HEALTH, 600.0)
                .add(Attributes.MOVEMENT_SPEED, SPEED)
                .add(Attributes.ATTACK_DAMAGE, 14.0)
                .add(Attributes.ARMOR, 14.0)
                .add(Attributes.ARMOR_TOUGHNESS, 8.0)
                .add(Attributes.KNOCKBACK_RESISTANCE, 1.0)
                .add(Attributes.FOLLOW_RANGE, 48.0);
    }

    @Override
    protected void defineSynchedData() {
        super.defineSynchedData();
        this.entityData.define(PHASE, PHASE_FIGHT);
    }

    @Override
    protected void registerGoals() {
        this.targetSelector.addGoal(1, new HurtByTargetGoal(this, WitherSkeleton.class));
        this.targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, 10, true, false,
                p -> !((Player) p).isCreative() && !p.isSpectator()));
    }

    // ---------------------------------------------------------------- state (public for the tests)
    public int phase() { return this.entityData.get(PHASE); }
    public boolean enraged() { return this.phase() == PHASE_ENRAGED; }
    public Action action() { return this.action; }
    public int minionsAlive() { return this.countMinions(); }
    public List<UUID> minionIds() { return this.minions; }
    /** invincible while kneeling among his minions and while he roars back to his feet */
    public boolean shielded() { return this.phase() == PHASE_KNEEL || this.action == Action.ROAR; }

    @Override public boolean removeWhenFarAway(double d) { return false; }
    @Override public boolean isPushable() { return false; }
    @Override public boolean canBeLeashed(Player p) { return false; }
    @Override protected boolean canRide(Entity e) { return false; }
    @Override public boolean isPersistenceRequired() { return true; }

    // ---------------------------------------------------------------- damage in
    @Override
    public boolean isInvulnerableTo(DamageSource source) {
        return source.is(DamageTypes.IN_WALL) || source.is(DamageTypes.FALL) || source.is(DamageTypes.DROWN)
                || source.is(DamageTypes.CRAMMING) || super.isInvulnerableTo(source);
    }

    /** harmful potion effects and spells' debuffs don't take hold on him */
    @Override
    public boolean canBeAffected(MobEffectInstance effect) {
        return effect.getEffect().getCategory() == MobEffectCategory.BENEFICIAL && super.canBeAffected(effect);
    }

    public static boolean isMagic(DamageSource source) {
        if (source.is(DamageTypeTags.WITCH_RESISTANT_TO) || source.is(DamageTypes.MAGIC) || source.is(DamageTypes.INDIRECT_MAGIC)
                || source.is(DamageTypes.SONIC_BOOM) || source.is(DamageTypes.DRAGON_BREATH) || source.is(DamageTypes.WITHER)) return true;
        String id = source.getMsgId().toLowerCase();
        if (id.contains("magic") || id.contains("spell") || id.contains("sonic") || id.contains("arcane")) return true;
        String ns = source.typeHolder().unwrapKey().map(ResourceKey::location).map(rl -> rl.getNamespace()).orElse("minecraft");
        return ns.equals("irons_spellbooks") || ns.equals("ars_nouveau") || ns.equals("ars_elemental") || ns.equals("traveloptics")
                || ns.equals("gtbcs_spell_lib") || ns.equals("ice_and_fire_spellbooks");
    }

    @Override
    public boolean hurt(DamageSource source, float amount) {
        boolean bypass = source.is(DamageTypeTags.BYPASSES_INVULNERABILITY);   // /kill, the void
        if (this.level().isClientSide) return super.hurt(source, amount);
        if (!bypass && this.shielded()) {
            if (this.tickCount % 4 == 0) {
                this.burst(ParticleTypes.ENCHANTED_HIT, this.position().add(0, 3, 0), 16, 1.0);
                this.sound(SoundEvents.ANVIL_LAND, 0.8f, 1.6f);
            }
            return false;
        }
        if (!bypass && source.getDirectEntity() instanceof Projectile proj && this.inFront(proj.position(), 75)) {
            boolean free = this.action == Action.NONE && this.gap <= 0;
            if (this.action == Action.BLOCK || (free && this.random.nextFloat() < 0.55f)) {
                this.sound(SoundEvents.SHIELD_BLOCK, 2f, 0.6f);
                this.burst(ParticleTypes.CRIT, proj.position(), 12, 0.2);
                Vec3 v = proj.getDeltaMovement();
                proj.setDeltaMovement(-v.x * 0.25, 0.2, -v.z * 0.25);
                if (free) { this.startAction(Action.BLOCK); this.actionLength = BLOCK_SHORT; }
                return false;
            }
        }
        if (!bypass && isMagic(source)) {
            amount *= MAGIC_TAKEN;
            this.burst(ParticleTypes.WITCH, this.position().add(0, 3, 0), 10, 1.0);
        }
        return super.hurt(source, amount);
    }

    // ---------------------------------------------------------------- boss bar
    @Override public void startSeenByPlayer(ServerPlayer player) { super.startSeenByPlayer(player); this.bossEvent.addPlayer(player); }
    @Override public void stopSeenByPlayer(ServerPlayer player) { super.stopSeenByPlayer(player); this.bossEvent.removePlayer(player); }

    // ---------------------------------------------------------------- server brain
    @Override
    protected void customServerAiStep() {
        super.customServerAiStep();
        this.bossEvent.setProgress(this.getHealth() / this.getMaxHealth());
        this.runPending();
        if (this.cdSweep > 0) this.cdSweep--;
        if (this.cdStomp > 0) this.cdStomp--;
        if (this.cdDash > 0) this.cdDash--;
        if (this.cdWave > 0) this.cdWave--;
        if (this.cdBlock > 0) this.cdBlock--;
        if (this.gap > 0) this.gap--;

        LivingEntity target = this.getTarget();
        if (target != null && (!target.isAlive() || (target instanceof Player p && (p.isCreative() || p.isSpectator())))) {
            this.setTarget(null);
            target = null;
        }

        if (this.action != Action.NONE) {
            this.tickAction(target);
            if (this.action != Action.NONE && this.action != Action.DASH) this.holdStill();
            return;
        }

        // half health: kneel and call the dead to fight for him (once)
        if (this.phase() == PHASE_FIGHT && this.getHealth() <= this.getMaxHealth() * 0.5f) {
            this.startAction(Action.KNEEL);
            this.entityData.set(PHASE, PHASE_KNEEL);
            this.sound(SoundEvents.IRON_GOLEM_DAMAGE, 2f, 0.5f);
            this.holdStill();
            return;
        }
        if (target == null) {
            this.getNavigation().stop();
            return;
        }

        double dist = this.flatDist(target);
        this.getLookControl().setLookAt(target, 30f, 30f);
        if (this.gap <= 0) {
            Action pick = this.choose(target, dist);
            if (pick != Action.NONE) {
                this.faceTarget(target, 360f);
                this.startAction(pick);
                this.holdStill();
                return;
            }
        }
        if (dist > 3.2) {
            double mult = dist > 12 ? 1.2 : 1.0;
            this.getNavigation().moveTo(target, mult);
        } else {
            this.getNavigation().stop();
            this.faceTarget(target, 12f);
        }
        if (this.tickCount % 14 == 0 && this.getDeltaMovement().horizontalDistanceSqr() > 0.003) {
            this.sound(SoundEvents.IRON_GOLEM_STEP, 1.6f, 0.6f);
        }
    }

    private Action choose(LivingEntity target, double d) {
        double dy = Math.abs(target.getY() - this.getY());
        ItemStack held = target.getMainHandItem();
        String heldId = String.valueOf(ForgeRegistries.ITEMS.getKey(held.getItem()));
        boolean ranged = held.getItem() instanceof ProjectileWeaponItem || held.getItem() instanceof TridentItem
                || heldId.contains("staff") || heldId.contains("wand");
        List<Action> opts = new ArrayList<>();
        List<Integer> weights = new ArrayList<>();
        if (d <= SWEEP_REACH + 0.5 && dy < 4 && this.cdSweep <= 0) { opts.add(Action.SWEEP); weights.add(5); }
        if (d <= STOMP_RADIUS && this.cdStomp <= 0) { opts.add(Action.STOMP); weights.add(d < 3.5 ? 5 : 3); }
        if (d >= DASH_MIN && d <= DASH_MAX && dy < 4 && this.cdDash <= 0 && this.hasLineOfSight(target)) { opts.add(Action.DASH); weights.add(4); }
        if (d <= WAVE_REACH && this.cdWave <= 0) { opts.add(Action.WAVE); weights.add(d < 4 ? 4 : 2); }
        if (ranged && d > 8 && this.cdBlock <= 0) { opts.add(Action.BLOCK); weights.add(6); }
        if (opts.isEmpty()) return Action.NONE;
        int sum = 0;
        for (int w : weights) sum += w;
        int r = this.random.nextInt(sum);
        for (int i = 0; i < opts.size(); i++) {
            r -= weights.get(i);
            if (r < 0) return opts.get(i);
        }
        return opts.get(0);
    }

    public void startAction(Action a) {
        this.action = a;
        this.actionTicks = 0;
        this.actionLength = switch (a) {
            case SWEEP -> SWEEP_LEN; case STOMP -> STOMP_LEN; case DASH -> DASH_LEN; case WAVE -> WAVE_LEN;
            case BLOCK -> BLOCK_LEN; case ROAR -> ROAR_LEN; default -> Integer.MAX_VALUE;
        };
        float cdMul = this.enraged() ? 0.7f : 1f;
        switch (a) {
            case SWEEP -> this.cdSweep = (int) (SWEEP_CD * cdMul);
            case STOMP -> this.cdStomp = (int) (STOMP_CD * cdMul);
            case DASH -> { this.cdDash = (int) (DASH_CD * cdMul); this.dashHit.clear(); }
            case WAVE -> this.cdWave = (int) (WAVE_CD * cdMul);
            case BLOCK -> this.cdBlock = (int) (BLOCK_CD * cdMul);
            default -> { }
        }
        this.getNavigation().stop();
        this.triggerAnim("main", a.anim);
    }

    private void finishAction() {
        this.action = Action.NONE;
        this.gap = GAP;
    }

    private void tickAction(@Nullable LivingEntity target) {
        int t = this.actionTicks++;
        float mul = this.enraged() ? 1.25f : 1f;
        boolean tracking = target != null && target.isAlive();
        switch (this.action) {
            case SWEEP -> {
                if (tracking && t < 6) this.faceTarget(target, 20f);
                if (t == 8) this.sound(SoundEvents.PLAYER_ATTACK_SWEEP, 2f, 0.5f);
                if (t == SWEEP_HIT) {
                    Vec3 f = this.forward();
                    this.burst(ParticleTypes.SWEEP_ATTACK, this.position().add(f.x * 3, 1.2, f.z * 3), 6, 1.2);
                    for (LivingEntity e : this.victims(SWEEP_REACH + 1.3)) {
                        if (this.flatDist(e) <= SWEEP_REACH + 1.3 && this.inFront(e.position(), SWEEP_ARC) && e.getY() < this.getY() + 3.5) {
                            if (this.strike(e, SWEEP_DMG * mul)) this.fling(e, 0.6, 0.25);
                        }
                    }
                }
            }
            case STOMP -> {
                if (t == STOMP_HIT) {
                    this.stompFx();
                    for (LivingEntity e : this.victims(STOMP_RADIUS + 1.3)) {
                        if (this.flatDist(e) <= STOMP_RADIUS + 1.3 && e.getY() < this.getY() + 2.5) {
                            if (this.strike(e, STOMP_DMG * mul)) this.fling(e, 0.25, 0.55);
                        }
                    }
                }
            }
            case DASH -> {
                if (t < DASH_GO) {
                    if (tracking) this.faceTarget(target, 30f);
                    this.dashYaw = this.getYRot();
                    this.holdStill();
                }
                if (t == DASH_GO) this.sound(SoundEvents.RAVAGER_ROAR, 2f, 1.4f);
                if (t >= DASH_GO && t < DASH_STOP) {
                    this.setYRot(this.dashYaw); this.yBodyRot = this.dashYaw; this.yHeadRot = this.dashYaw;
                    Vec3 f = this.forward();
                    this.setDeltaMovement(f.x * DASH_SPEED, this.getDeltaMovement().y, f.z * DASH_SPEED);
                    this.hasImpulse = true;
                    this.burst(ParticleTypes.CLOUD, this.position(), 6, 0.8);
                    AABB reach = this.getBoundingBox().inflate(1.4);
                    for (LivingEntity e : this.level().getEntitiesOfClass(LivingEntity.class, reach, this::canHit)) {
                        if (!this.dashHit.contains(e.getUUID())) {
                            this.dashHit.add(e.getUUID());
                            if (this.strike(e, DASH_DMG * mul)) this.push(e, f.x, f.z, 1.0, 0.45);
                        }
                    }
                    if (this.horizontalCollision && t > DASH_GO + 1) {
                        this.actionTicks = DASH_STOP;
                        this.holdStill();
                    }
                }
                if (t >= DASH_STOP) this.holdStill();
            }
            case WAVE -> {
                if (tracking && t < 8) this.faceTarget(target, 20f);
                if (t == WAVE_HIT) {
                    Vec3 f = this.forward();
                    if (this.level() instanceof ServerLevel sl) {
                        for (int s = 1; s <= 7; s++) {
                            sl.sendParticles(ParticleTypes.SONIC_BOOM, this.getX() + f.x * s * 1.1, this.getY() + 4.2, this.getZ() + f.z * s * 1.1, 1, 0, 0, 0, 0);
                        }
                    }
                    this.sound(SoundEvents.WARDEN_SONIC_BOOM, 2f, 1.3f);
                    for (LivingEntity e : this.victims(WAVE_REACH + 1)) {
                        if (this.inFront(e.position(), WAVE_ARC)) {
                            this.strike(e, WAVE_DMG * mul);
                            this.fling(e, WAVE_PUSH, 0.45);          // thrown 5-6 blocks back
                        }
                    }
                }
            }
            case BLOCK -> {
                if (tracking) this.faceTarget(target, 20f);
            }
            case KNEEL -> {
                if (t == KNEEL_SUMMON) {
                    this.summonMinions(target);
                    this.sound(SoundEvents.WITHER_SPAWN, 2f, 0.7f);
                }
                if (t % 6 == 0) this.burst(ParticleTypes.ENCHANT, this.position().add(0, 3, 0), 12, 1.4);
                if (t > KNEEL_SUMMON + 40 && t % 10 == 0 && this.countMinions() == 0) {
                    this.startAction(Action.ROAR);       // all his dead are dead again: he rises
                    return;
                }
            }
            case ROAR -> {
                if (t == 10) this.sound(SoundEvents.ENDER_DRAGON_GROWL, 3f, 0.6f);
                if (t == ROAR_GLOW) {
                    this.entityData.set(PHASE, PHASE_ENRAGED);
                    this.getAttribute(Attributes.MOVEMENT_SPEED).setBaseValue(SPEED_ENRAGED);
                    this.burst(ParticleTypes.DRAGON_BREATH, this.position().add(0, 4, 0), 120, 2.0);
                    this.burst(ParticleTypes.FLASH, this.position().add(0, 5, 0), 1, 0);
                    for (LivingEntity e : this.victims(7)) this.fling(e, 0.5, 0.3);
                }
            }
            default -> { }
        }
        if (this.actionTicks >= this.actionLength) this.finishAction();
    }

    // ---------------------------------------------------------------- minions
    private void summonMinions(@Nullable LivingEntity target) {
        if (!(this.level() instanceof ServerLevel sl)) return;
        this.minions.clear();
        for (int k = 0; k < MINIONS; k++) {
            final int idx = k;
            this.later(k * 4, () -> {
                double a = (idx / (double) MINIONS) * Math.PI * 2, r = 5 + this.random.nextDouble() * 2.5;
                double x = this.getX() + Math.cos(a) * r, z = this.getZ() + Math.sin(a) * r;
                double y = this.groundY(x, z);
                WitherSkeleton w = EntityType.WITHER_SKELETON.create(sl);
                if (w == null) return;
                w.moveTo(x, y, z, this.random.nextFloat() * 360f, 0);
                w.finalizeSpawn(sl, sl.getCurrentDifficultyAt(BlockPos.containing(x, y, z)), MobSpawnType.MOB_SUMMONED, null, null);
                w.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(Items.STONE_SWORD));
                w.setItemSlot(EquipmentSlot.HEAD, new ItemStack(Items.CHAINMAIL_HELMET));
                w.setItemSlot(EquipmentSlot.CHEST, new ItemStack(Items.IRON_CHESTPLATE));
                w.setItemSlot(EquipmentSlot.LEGS, new ItemStack(Items.CHAINMAIL_LEGGINGS));
                w.setItemSlot(EquipmentSlot.FEET, new ItemStack(Items.CHAINMAIL_BOOTS));
                for (EquipmentSlot s : EquipmentSlot.values()) w.setDropChance(s, 0f);
                w.setPersistenceRequired();
                w.addTag("gate_knight_minion");
                LivingEntity tgt = this.getTarget();
                if (tgt != null) w.setTarget(tgt);
                sl.addFreshEntity(w);
                this.minions.add(w.getUUID());
                sl.sendParticles(ParticleTypes.SOUL_FIRE_FLAME, x, y + 1, z, 30, 0.4, 1, 0.4, 0.02);
                sl.sendParticles(ParticleTypes.LARGE_SMOKE, x, y + 0.6, z, 20, 0.4, 0.6, 0.4, 0.02);
                this.sound(SoundEvents.WITHER_SKELETON_AMBIENT, 1.5f, 0.6f);
            });
        }
        this.minionsSpawnedAt = this.tickCount;
    }

    private int countMinions() {
        if (!(this.level() instanceof ServerLevel sl)) return 0;
        int n = 0;
        for (UUID id : this.minions) {
            Entity e = sl.getEntity(id);
            if (e != null && e.isAlive()) n++;
        }
        // all 9 are summoned over ~32 ticks; until then the count can't be zero
        if (this.minions.size() < MINIONS && this.action == Action.KNEEL) n = Math.max(n, 1);
        return n;
    }

    private void killMinions() {
        if (!(this.level() instanceof ServerLevel sl)) return;
        for (UUID id : this.minions) {
            Entity e = sl.getEntity(id);
            if (e != null && e.isAlive()) e.kill();
        }
        this.minions.clear();
    }

    // ---------------------------------------------------------------- stomp: the ground heaves up in rings
    private void stompFx() {
        if (!(this.level() instanceof ServerLevel sl)) return;
        int cx = Mth.floor(this.getX()), cz = Mth.floor(this.getZ()), y = Mth.floor(this.getY());
        String tag = "gk_fx_" + this.getId() + "_" + this.tickCount;
        for (int r = 2; r <= (int) STOMP_RADIUS; r++) {
            int count = Math.round(r * 4.5f);
            for (int k = 0; k < count; k++) {
                double a = (k / (double) count) * Math.PI * 2 + r * 0.37;
                int x = Mth.floor(cx + Math.cos(a) * r), z = Mth.floor(cz + Math.sin(a) * r);
                int yy = y;
                for (int s = 0; s < 3 && sl.getBlockState(new BlockPos(x, yy - 1, z)).isAir(); s++) yy--;
                BlockState bs = sl.getBlockState(new BlockPos(x, yy - 1, z));
                if (bs.isAir() || !bs.getFluidState().isEmpty()) continue;
                String id = String.valueOf(ForgeRegistries.BLOCKS.getKey(bs.getBlock()));
                final int fx = x, fy = yy - 1, fz = z, ring = r;
                this.later(r - 1, () -> {
                    this.command("summon block_display " + fx + " " + fy + " " + fz + " {block_state:{Name:\"" + id + "\"},Tags:[\"" + tag + "\",\"" + tag + "_" + ring + "\"]}");
                    sl.sendParticles(new BlockParticleOption(ParticleTypes.BLOCK, bs), fx + 0.5, fy + 1.2, fz + 0.5, 6, 0.3, 0.2, 0.3, 0.1);
                });
            }
            final int ring = r;
            final String up = String.format(java.util.Locale.ROOT, "%.2f", 0.55 + this.random.nextDouble() * 0.5);
            this.later(r, () -> this.command("execute as @e[type=block_display,tag=" + tag + "_" + ring + "] run data merge entity @s "
                    + "{start_interpolation:0,interpolation_duration:3,transformation:{translation:[0f," + up + "f,0f],left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],scale:[1f,1f,1f]}}"));
            this.later(r + 10, () -> this.command("execute as @e[type=block_display,tag=" + tag + "_" + ring + "] run data merge entity @s "
                    + "{start_interpolation:0,interpolation_duration:6,transformation:{translation:[0f,0f,0f],left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f],scale:[1f,1f,1f]}}"));
        }
        this.later((int) STOMP_RADIUS + 20, () -> this.command("kill @e[type=block_display,tag=" + tag + "]"));
        this.burst(ParticleTypes.EXPLOSION, this.position(), 6, 1.5);
        this.sound(SoundEvents.GENERIC_EXPLODE, 2.5f, 0.6f);
        this.sound(SoundEvents.IRON_GOLEM_ATTACK, 2.5f, 0.5f);
    }

    // ---------------------------------------------------------------- death: one knee, hands and head on the hilt, then dust
    @Override
    public void die(DamageSource source) {
        super.die(source);
        if (!this.level().isClientSide) {
            this.action = Action.NONE;
            this.pending.clear();
            this.triggerAnim("main", "death");
            this.sound(SoundEvents.WITHER_DEATH, 2f, 0.6f);
            this.killMinions();
            this.bossEvent.removeAllPlayers();
        }
    }

    @Override
    protected void tickDeath() {
        ++this.deathTime;
        if (this.level() instanceof ServerLevel sl) {
            if (this.deathTime > 40 && this.deathTime % 2 == 0) {
                float k = Math.min(1f, (this.deathTime - 40) / 30f);
                sl.sendParticles(ParticleTypes.WHITE_ASH, this.getX(), this.getY() + 3, this.getZ(), (int) (20 + 60 * k), 1.4, 3, 1.4, 0.02);
                sl.sendParticles(ParticleTypes.ASH, this.getX(), this.getY() + 3, this.getZ(), (int) (10 + 40 * k), 1.2, 2.8, 1.2, 0.02);
            }
            if (this.deathTime == 66) this.sound(SoundEvents.SAND_BREAK, 2f, 0.5f);
            if (this.deathTime >= 72 && !this.isRemoved()) {
                sl.sendParticles(ParticleTypes.LARGE_SMOKE, this.getX(), this.getY() + 3, this.getZ(), 60, 1.4, 3, 1.4, 0.03);
                this.sound(SoundEvents.SOUL_SAND_BREAK, 2f, 0.6f);
                this.level().broadcastEntityEvent(this, (byte) 60);
                this.remove(RemovalReason.KILLED);
            }
        }
    }

    // ---------------------------------------------------------------- helpers
    private boolean canHit(LivingEntity e) {
        if (e == this || !e.isAlive() || e instanceof GateKnightEntity || e.getTags().contains("gate_knight_minion")) return false;
        if (e instanceof Player p) return !p.isCreative() && !p.isSpectator();
        return true;
    }

    private List<LivingEntity> victims(double r) {
        return this.level().getEntitiesOfClass(LivingEntity.class, this.getBoundingBox().inflate(r, 4, r),
                e -> this.canHit(e) && this.flatDist(e) <= r + 1.5);
    }

    /** deals damage as a mob attack; true if it landed */
    private boolean strike(LivingEntity e, float dmg) {
        return e.hurt(this.damageSources().mobAttack(this), dmg);
    }

    /** throw away from him */
    private void fling(LivingEntity e, double h, double up) {
        this.push(e, e.getX() - this.getX(), e.getZ() - this.getZ(), h, up);
    }

    private void push(LivingEntity e, double dx, double dz, double h, double up) {
        double d = Math.sqrt(dx * dx + dz * dz);
        if (d < 1e-4) { Vec3 f = this.forward(); dx = f.x; dz = f.z; d = 1; }
        double kr = 1.0 - e.getAttributeValue(Attributes.KNOCKBACK_RESISTANCE) * 0.5;
        e.setDeltaMovement(dx / d * h * kr, up, dz / d * h * kr);
        e.hasImpulse = true;
        e.hurtMarked = true;                     // makes the server send the new velocity to the player
    }

    private double flatDist(Entity e) {
        double dx = e.getX() - this.getX(), dz = e.getZ() - this.getZ();
        return Math.sqrt(dx * dx + dz * dz);
    }

    private Vec3 forward() {
        float yaw = this.getYRot() * Mth.DEG_TO_RAD;
        return new Vec3(-Mth.sin(yaw), 0, Mth.cos(yaw));
    }

    private boolean inFront(Vec3 p, double halfAngle) {
        Vec3 f = this.forward();
        double dx = p.x - this.getX(), dz = p.z - this.getZ(), d = Math.sqrt(dx * dx + dz * dz);
        if (d < 1.6) return true;
        return (f.x * dx + f.z * dz) / d >= Math.cos(Math.toRadians(halfAngle));
    }

    private void faceTarget(LivingEntity target, float maxTurn) {
        double dx = target.getX() - this.getX(), dz = target.getZ() - this.getZ();
        float want = (float) (Mth.atan2(dz, dx) * Mth.RAD_TO_DEG) - 90f;
        float yaw = Mth.approachDegrees(this.getYRot(), want, maxTurn);
        this.setYRot(yaw); this.yBodyRot = yaw; this.yHeadRot = yaw;
    }

    private void holdStill() {
        this.getNavigation().stop();
        this.setXxa(0); this.setZza(0); this.setSpeed(0);
        Vec3 v = this.getDeltaMovement();
        this.setDeltaMovement(0, v.y, 0);
    }

    private double groundY(double x, double z) {
        BlockPos.MutableBlockPos p = new BlockPos.MutableBlockPos(Mth.floor(x), Mth.floor(this.getY()) + 3, Mth.floor(z));
        for (int i = 0; i < 10; i++) {
            if (!this.level().getBlockState(p.below()).isAir() && this.level().getBlockState(p).isAir() && this.level().getBlockState(p.above()).isAir()) return p.getY();
            p.move(0, -1, 0);
        }
        return this.getY();
    }

    private void burst(ParticleOptions type, Vec3 c, int count, double spread) {
        if (this.level() instanceof ServerLevel sl) sl.sendParticles(type, c.x, c.y, c.z, count, spread, spread * 0.5, spread, 0.05);
    }

    private void sound(SoundEvent s, float vol, float pitch) {
        this.level().playSound(null, this.getX(), this.getY(), this.getZ(), s, SoundSource.HOSTILE, vol, pitch);
    }

    private void command(String cmd) {
        if (this.level() instanceof ServerLevel sl) {
            sl.getServer().getCommands().performPrefixedCommand(
                    sl.getServer().createCommandSourceStack().withLevel(sl).withSuppressedOutput().withPermission(4), cmd);
        }
    }

    private void later(int ticks, Runnable r) { this.pending.add(new Pending(this.tickCount + ticks, r)); }

    private void runPending() {
        if (this.pending.isEmpty()) return;
        List<Pending> due = new ArrayList<>();
        for (Iterator<Pending> it = this.pending.iterator(); it.hasNext(); ) {
            Pending p = it.next();
            if (p.at() <= this.tickCount) { due.add(p); it.remove(); }
        }
        for (Pending p : due) p.run().run();
    }

    @Override protected SoundEvent getHurtSound(DamageSource s) { return SoundEvents.IRON_GOLEM_HURT; }
    @Override protected SoundEvent getDeathSound() { return null; }
    @Override protected float getSoundVolume() { return 2.0f; }

    // ---------------------------------------------------------------- save / load
    @Override
    public void addAdditionalSaveData(CompoundTag tag) {
        super.addAdditionalSaveData(tag);
        tag.putInt("GkPhase", this.phase());
        ListTag list = new ListTag();
        for (UUID id : this.minions) list.add(NbtUtils.createUUID(id));
        tag.put("GkMinions", list);
    }

    @Override
    public void readAdditionalSaveData(CompoundTag tag) {
        super.readAdditionalSaveData(tag);
        int ph = tag.getInt("GkPhase");
        this.entityData.set(PHASE, ph);
        this.minions.clear();
        for (Tag t : tag.getList("GkMinions", Tag.TAG_INT_ARRAY)) this.minions.add(NbtUtils.loadUUID(t));
        if (ph == PHASE_KNEEL) {                  // reloaded mid-kneel: keep watching the minions
            this.action = Action.KNEEL;
            this.actionTicks = KNEEL_SUMMON + 1;
            this.actionLength = Integer.MAX_VALUE;
        }
        if (ph == PHASE_ENRAGED) this.getAttribute(Attributes.MOVEMENT_SPEED).setBaseValue(SPEED_ENRAGED);
    }

    @Override
    public void setCustomName(@Nullable Component name) {
        super.setCustomName(name);
        this.bossEvent.setName(this.getDisplayName());
    }

    // ---------------------------------------------------------------- GeckoLib: one controller; attacks are triggered on it so they replace walk/idle
    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
        controllers.add(new AnimationController<>(this, "main", 4, state -> {
            if (this.phase() == PHASE_KNEEL) return state.setAndContinue(KNEEL_HOLD);
            if (state.isMoving()) return state.setAndContinue(WALK);
            return state.setAndContinue(IDLE);
        })
                .triggerableAnim("sweep", RawAnimation.begin().thenPlay("sweep"))
                .triggerableAnim("stomp", RawAnimation.begin().thenPlay("stomp"))
                .triggerableAnim("dash", RawAnimation.begin().thenPlay("dash"))
                .triggerableAnim("shockwave", RawAnimation.begin().thenPlay("shockwave"))
                .triggerableAnim("block", RawAnimation.begin().thenPlay("block"))
                .triggerableAnim("kneel", RawAnimation.begin().thenPlayAndHold("kneel"))
                .triggerableAnim("roar", RawAnimation.begin().thenPlay("roar"))
                .triggerableAnim("death", RawAnimation.begin().thenPlayAndHold("death")));
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() { return this.cache; }
}
