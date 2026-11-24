package com.aof.gateknight.test;

import com.aof.gateknight.GateKnightMod;
import com.aof.gateknight.entity.GateKnightEntity;
import com.aof.gateknight.entity.GateKnightEntity.Action;
import com.mojang.logging.LogUtils;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.monster.WitherSkeleton;
import net.minecraft.world.entity.monster.Zombie;
import net.minecraft.world.entity.projectile.Arrow;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.gametest.GameTestHolder;
import net.minecraftforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.util.UUID;

/** Automated in-game checks of every part of the fight. */
@GameTestHolder(GateKnightMod.MODID)
@PrefixGameTestTemplate(false)
public class GateKnightTests {
    private static final Logger LOG = LogUtils.getLogger();

    private static GateKnightEntity knight(GameTestHelper h, int x, int z) {
        GateKnightEntity g = h.spawn(GateKnightMod.GATE_KNIGHT.get(), x, 2, z);
        g.setYRot(0); g.yBodyRot = 0; g.yHeadRot = 0;          // facing +z
        return g;
    }

    private static Zombie dummy(GameTestHelper h, double x, double z) {
        Zombie d = h.spawn(EntityType.ZOMBIE, new Vec3(x, 2, z));
        d.setNoAi(true);
        d.getAttribute(Attributes.MAX_HEALTH).setBaseValue(500);
        d.setHealth(500);
        d.getAttribute(Attributes.KNOCKBACK_RESISTANCE).setBaseValue(0);
        return d;
    }

    /** he walks to a target on his own, faster than a walking player (4.3 blocks/s) */
    @GameTest(template = "arena", timeoutTicks = 300)
    public static void walksToTarget(GameTestHelper h) {
        GateKnightEntity g = knight(h, 16, 3);
        Zombie z = dummy(h, 16.5, 29.5);
        final Vec3[] start = new Vec3[1];
        h.runAfterDelay(2, () -> g.setTarget(z));
        h.runAfterDelay(20, () -> start[0] = g.position());
        h.runAfterDelay(60, () -> {
            double moved = g.position().distanceTo(start[0]);
            double bps = moved / 2.0;
            LOG.info("[GateKnightTest] walk speed {} blocks/s", String.format("%.2f", bps));
            h.assertTrue(bps > 4.3, "walks " + bps + " blocks/s, should beat a walking player (4.3)");
            h.succeed();
        });
    }

    private static void attackTest(GameTestHelper h, Action a, double dz, String what) {
        GateKnightEntity g = knight(h, 16, 6);
        Zombie z = dummy(h, 16.5, 6.5 + dz);
        h.runAfterDelay(3, () -> { g.setTarget(z); g.startAction(a); });
        h.succeedWhen(() -> {
            h.assertTrue(z.getHealth() < 500, what + ": target not hurt yet");
            LOG.info("[GateKnightTest] {} hit for {} at {} blocks", what, 500 - z.getHealth(), dz);
        });
    }

    @GameTest(template = "arena", timeoutTicks = 80) public static void sweepHits(GameTestHelper h) { attackTest(h, Action.SWEEP, 4.5, "sweep"); }
    @GameTest(template = "arena", timeoutTicks = 80) public static void stompHits(GameTestHelper h) { attackTest(h, Action.STOMP, 5.0, "stomp"); }
    @GameTest(template = "arena", timeoutTicks = 80) public static void dashHits(GameTestHelper h) { attackTest(h, Action.DASH, 10.0, "dash"); }
    @GameTest(template = "arena", timeoutTicks = 80) public static void shockwaveHits(GameTestHelper h) { attackTest(h, Action.WAVE, 4.0, "shockwave"); }

    /** the shockwave throws its target 5-6 blocks back */
    @GameTest(template = "arena", timeoutTicks = 120)
    public static void shockwavePushes(GameTestHelper h) {
        GateKnightEntity g = knight(h, 16, 4);
        Zombie z = h.spawn(EntityType.ZOMBIE, new Vec3(16.5, 2, 8.5));
        z.setNoAi(true);
        h.runAfterDelay(3, () -> { g.setTarget(z); g.startAction(Action.WAVE); });
        h.runAfterDelay(80, () -> {
            double pushed = z.position().z - 8.5;
            LOG.info("[GateKnightTest] shockwave pushed {} blocks", String.format("%.2f", pushed));
            h.assertTrue(pushed >= 4.5 && pushed <= 8.0, "pushed " + pushed + " blocks, wanted 5-6");
            h.succeed();
        });
    }

    /** the dash carries him ~10 blocks */
    @GameTest(template = "arena", timeoutTicks = 80)
    public static void dashDistance(GameTestHelper h) {
        GateKnightEntity g = knight(h, 16, 3);
        Zombie z = dummy(h, 16.5, 29.5);
        final double[] z0 = new double[1];
        h.runAfterDelay(3, () -> { g.setTarget(z); z0[0] = g.getZ(); g.startAction(Action.DASH); });
        h.runAfterDelay(40, () -> {
            double d = g.getZ() - z0[0];
            LOG.info("[GateKnightTest] dash covered {} blocks", String.format("%.2f", d));
            h.assertTrue(d >= 8 && d <= 13, "dash covered " + d + " blocks, wanted ~10");
            h.succeed();
        });
    }

    /** arrows from the front bounce off his raised sword */
    @GameTest(template = "arena", timeoutTicks = 80)
    public static void blocksArrows(GameTestHelper h) {
        GateKnightEntity g = knight(h, 16, 6);
        h.runAfterDelay(3, () -> g.startAction(Action.BLOCK));
        h.runAfterDelay(8, () -> {
            Arrow arrow = new Arrow(h.getLevel(), h.absoluteVec(new Vec3(16.5, 5, 16)).x, h.absoluteVec(new Vec3(16.5, 5, 16)).y, h.absoluteVec(new Vec3(16.5, 5, 16)).z);
            arrow.setDeltaMovement(0, 0, -2.5);
            arrow.setBaseDamage(10);
            h.getLevel().addFreshEntity(arrow);
        });
        h.runAfterDelay(40, () -> {
            h.assertTrue(g.getHealth() == g.getMaxHealth(), "arrow got through the block: " + g.getHealth());
            h.succeed();
        });
    }

    /** magic does 15% */
    @GameTest(template = "arena", timeoutTicks = 40)
    public static void resistsMagic(GameTestHelper h) {
        GateKnightEntity g = knight(h, 16, 16);
        h.runAfterDelay(3, () -> {
            g.hurt(h.getLevel().damageSources().magic(), 100f);
            float lost = g.getMaxHealth() - g.getHealth();
            LOG.info("[GateKnightTest] 100 magic damage -> lost {}", lost);
            h.assertTrue(lost > 0 && lost <= 16, "magic took " + lost + " of 100");
            h.succeed();
        });
    }

    /** at half health: kneels, invincible, 9 wither skeletons rise; when they all die he roars, glows and fights on */
    @GameTest(template = "arena", timeoutTicks = 400)
    public static void kneelPhase(GameTestHelper h) {
        GateKnightEntity g = knight(h, 16, 16);
        h.runAfterDelay(3, () -> g.setHealth(290f));
        h.runAfterDelay(6, () -> h.assertTrue(g.action() == Action.KNEEL && g.phase() == GateKnightEntity.PHASE_KNEEL, "did not kneel at half health: " + g.action()));
        h.runAfterDelay(30, () -> {
            float hp = g.getHealth();
            g.invulnerableTime = 0;
            g.hurt(h.getLevel().damageSources().generic(), 50f);
            g.hurt(h.getLevel().damageSources().magic(), 50f);
            h.assertTrue(g.getHealth() == hp, "took damage while kneeling: " + hp + " -> " + g.getHealth());
        });
        h.runAfterDelay(90, () -> {
            int n = 0;
            for (UUID id : g.minionIds()) {
                Entity e = h.getLevel().getEntity(id);
                if (e instanceof WitherSkeleton && e.isAlive()) n++;
            }
            LOG.info("[GateKnightTest] minions alive after summoning: {}", n);
            h.assertTrue(n == 9, "expected 9 wither skeletons, found " + n);
            h.assertTrue(g.action() == Action.KNEEL, "should still be kneeling while minions live");
            for (UUID id : g.minionIds()) { Entity e = h.getLevel().getEntity(id); if (e != null) e.kill(); }
        });
        h.runAfterDelay(120, () -> h.assertTrue(g.action() == Action.ROAR, "should roar once the minions are dead: " + g.action()));
        h.runAfterDelay(200, () -> {
            h.assertTrue(g.enraged(), "should be enraged after the roar");
            h.assertTrue(g.action() != Action.ROAR && g.action() != Action.KNEEL, "should be fighting again: " + g.action());
            float hp = g.getHealth();
            g.invulnerableTime = 0;
            g.hurt(h.getLevel().damageSources().generic(), 20f);
            h.assertTrue(g.getHealth() < hp, "should take damage again after standing up");
            h.succeed();
        });
    }

    /** death: kneels on his sword for 3.4 s then crumbles away */
    @GameTest(template = "arena", timeoutTicks = 200)
    public static void diesAndCrumbles(GameTestHelper h) {
        GateKnightEntity g = knight(h, 16, 16);
        h.runAfterDelay(3, () -> g.hurt(h.getLevel().damageSources().genericKill(), 10000f));
        h.runAfterDelay(40, () -> h.assertTrue(!g.isRemoved(), "removed too early, the death animation must play"));
        h.runAfterDelay(100, () -> { h.assertTrue(g.isRemoved(), "should have crumbled away"); h.succeed(); });
    }
}
