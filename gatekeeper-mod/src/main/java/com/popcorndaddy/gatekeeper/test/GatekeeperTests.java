package com.popcorndaddy.gatekeeper.test;

import com.popcorndaddy.gatekeeper.GatekeeperMod;
import com.popcorndaddy.gatekeeper.entity.GatekeeperEntity;
import com.popcorndaddy.gatekeeper.portal.PortalData;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.monster.Zombie;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.common.util.FakePlayer;
import net.minecraftforge.common.util.FakePlayerFactory;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.gametest.GameTestHolder;
import net.minecraftforge.gametest.PrefixGameTestTemplate;

/** Automated in-game tests (run with: gradlew runGameTestServer). */
@GameTestHolder(GatekeeperMod.MODID)
@PrefixGameTestTemplate(false)
public class GatekeeperTests {

    private static GatekeeperEntity spawn(GameTestHelper h, int x, int z) {
        return h.spawn(GatekeeperMod.GATEKEEPER.get(), x, 2, z);
    }

    /** A survival test player standing at (x, z) in the arena (he only ever fights players). */
    private static net.minecraft.world.entity.player.Player player(GameTestHelper h, int x, int z, float hp) {
        ServerLevel level = h.getLevel();
        net.minecraft.world.entity.player.Player p = new net.minecraft.world.entity.player.Player(level, BlockPos.ZERO, 0f,
                new com.mojang.authlib.GameProfile(java.util.UUID.randomUUID(), "test-player")) {
            @Override public boolean isSpectator() { return false; }
            @Override public boolean isCreative() { return false; }
        };
        Vec3 at = h.absoluteVec(new Vec3(x + 0.5, 2, z + 0.5));
        p.moveTo(at.x, at.y, at.z, 0, 0);
        p.getAttribute(net.minecraft.world.entity.ai.attributes.Attributes.MAX_HEALTH).setBaseValue(hp);
        p.setHealth(hp);
        level.addFreshEntity(p);
        return p;
    }

    /** Dormant guardians ignore damage; once awakened he goes through the awakening + entrance and starts fighting. */
    @GameTest(template = "arena", timeoutTicks = 400)
    public static void awakensAndFights(GameTestHelper h) {
        GatekeeperEntity g = spawn(h, 12, 12);
        h.runAfterDelay(5, () -> {
            h.assertTrue(g.phase() == GatekeeperEntity.PHASE_DORMANT, "should start dormant");
            g.hurt(h.getLevel().damageSources().generic(), 50f);
            h.assertTrue(g.getHealth() == g.getMaxHealth(), "dormant guardian must not take damage");
            g.startAwakening();
        });
        h.runAfterDelay(60, () -> {
            h.assertTrue(g.phase() == GatekeeperEntity.PHASE_AWAKENING, "should be awakening");
            h.assertFalse(g.eyesOpen(), "eyes open too early");
        });
        h.runAfterDelay(140, () -> h.assertTrue(g.eyesOpen(), "eyes should be open after the awakening"));
        h.runAfterDelay(215, () -> {
            h.assertTrue(g.phase() == GatekeeperEntity.PHASE_FIGHT, "should be fighting after the entrance");
            h.succeed();
        });
    }

    /** In the fight he walks to a player and his attacks deal damage. */
    @GameTest(template = "arena", timeoutTicks = 500)
    public static void attacksHit(GameTestHelper h) {
        GatekeeperEntity g = spawn(h, 12, 8);
        net.minecraft.world.entity.player.Player p = player(h, 12, 17, 400);
        h.runAfterDelay(2, () -> { g.startAwakening(); });
        h.runAfterDelay(200, () -> g.setTarget(p));
        h.succeedWhen(() -> h.assertTrue(p.getHealth() < 400 || !p.isAlive(), "player not damaged yet"));
    }

    /** He fights players only: a zombie beside the fight is never hit, and a zombie that strikes him is not targeted. */
    @GameTest(template = "arena", timeoutTicks = 500)
    public static void ignoresOtherMobs(GameTestHelper h) {
        GatekeeperEntity g = spawn(h, 12, 8);
        Zombie z = h.spawn(EntityType.ZOMBIE, 13, 2, 11);
        z.setNoAi(true);
        z.getAttribute(net.minecraft.world.entity.ai.attributes.Attributes.MAX_HEALTH).setBaseValue(400);
        z.setHealth(400);
        h.runAfterDelay(2, g::startAwakening);
        h.runAfterDelay(200, () -> {
            g.hurt(g.damageSources().mobAttack(z), 1.0f);
            h.assertFalse(g.canAttack(z), "a zombie must never be a valid target");
            h.assertTrue(g.forceGravityWell(), "gravity well should start");
        });
        h.runAfterDelay(200 + GatekeeperEntity.GW_BURST + 20, () -> {
            h.assertTrue(z.getHealth() >= 400, "the zombie was hurt: " + z.getHealth());
            h.assertTrue(g.getTarget() != z, "he turned on the zombie");
            h.succeed();
        });
    }

    /** Gravity well: a target 10 blocks away is dragged in during the 3-second channel, then thrown back out by the burst. */
    @GameTest(template = "arena", timeoutTicks = 400)
    public static void gravityWellPullsThenBursts(GameTestHelper h) {
        GatekeeperEntity g = spawn(h, 12, 6);
        net.minecraft.world.entity.player.Player stand = player(h, 12, 16, 400);
        double[] d = new double[3];
        h.runAfterDelay(2, g::startAwakening);
        h.runAfterDelay(200, () -> {
            h.assertTrue(g.phase() == GatekeeperEntity.PHASE_FIGHT, "should be fighting before the well");
            d[0] = g.distanceTo(stand);
            h.assertTrue(g.forceGravityWell(), "gravity well should start");
            h.assertTrue(g.usingGravityWell(), "should be channelling");
        });
        h.runAfterDelay(200 + GatekeeperEntity.GW_BURST - 2, () -> {
            d[1] = g.distanceTo(stand);
            h.assertTrue(g.usingGravityWell(), "still channelling just before the burst");
            h.assertTrue(d[1] < d[0] - 4.0, "target should be pulled in: " + d[0] + " -> " + d[1]);
        });
        h.runAfterDelay(200 + GatekeeperEntity.GW_BURST + 14, () -> {
            d[2] = g.distanceTo(stand);
            h.assertTrue(d[2] > d[1] + 2.0, "burst should throw the target out: " + d[1] + " -> " + d[2]);
        });
        h.runAfterDelay(200 + 104, () -> {
            h.assertFalse(g.usingGravityWell(), "the well should end after 100 ticks");
            h.succeed();
        });
    }

    /** Mods that hand out random mob names (Villager Names) must not rename him. */
    @GameTest(template = "arena", timeoutTicks = 40)
    public static void keepsHisName(GameTestHelper h) {
        GatekeeperEntity g = spawn(h, 12, 12);
        g.setCustomName(net.minecraft.network.chat.Component.literal("Joanna"));
        h.assertFalse(g.hasCustomName(), "custom name should be ignored");
        h.assertTrue(g.getDisplayName().getString().equals(net.minecraft.network.chat.Component.translatable("entity.aof_gatekeeper.gatekeeper").getString()),
                "display name should stay the Gatekeeper's, was " + g.getDisplayName().getString());
        h.succeed();
    }

    /** At half health he enrages (rage animation, then enraged state). */
    @GameTest(template = "arena", timeoutTicks = 400)
    public static void enragesAtHalfHealth(GameTestHelper h) {
        GatekeeperEntity g = spawn(h, 12, 12);
        h.runAfterDelay(2, g::startAwakening);
        h.runAfterDelay(200, () -> g.setHealth(g.getMaxHealth() * 0.45f));
        h.succeedWhen(() -> h.assertTrue(g.enraged(), "not enraged yet"));
    }

    /** Death plays out (~87 ticks), then he is removed and drops his loot. */
    @GameTest(template = "arena", timeoutTicks = 400)
    public static void diesAndDropsLoot(GameTestHelper h) {
        GatekeeperEntity g = spawn(h, 12, 12);
        h.runAfterDelay(2, g::startAwakening);
        h.runAfterDelay(200, () -> g.hurt(h.getLevel().damageSources().fellOutOfWorld(), 5000f));
        h.runAfterDelay(320, () -> {
            h.assertTrue(g.isRemoved(), "should be removed after the death animation");
            boolean diamonds = !h.getLevel().getEntitiesOfClass(ItemEntity.class, g.getBoundingBox().inflate(8),
                    i -> i.getItem().is(Items.DIAMOND)).isEmpty();
            h.assertTrue(diamonds, "loot (diamonds) should have dropped");
            h.succeed();
        });
    }

    /** A ring of End portal frames is sealed while its guardian lives, and opens once he is defeated. */
    @GameTest(template = "arena", timeoutTicks = 100)
    public static void portalSeal(GameTestHelper h) {
        BlockPos c = new BlockPos(12, 2, 12);
        PortalData.get(h.getLevel()).forgetNear(h.absolutePos(c), 32);     // the test world persists between runs
        for (int i = -1; i <= 1; i++) {
            h.setBlock(c.offset(i, 0, -2), Blocks.END_PORTAL_FRAME);
            h.setBlock(c.offset(i, 0, 2), Blocks.END_PORTAL_FRAME);
            h.setBlock(c.offset(-2, 0, i), Blocks.END_PORTAL_FRAME);
            h.setBlock(c.offset(2, 0, i), Blocks.END_PORTAL_FRAME);
        }
        ServerLevel level = h.getLevel();
        FakePlayer player = FakePlayerFactory.getMinecraft(level);
        BlockPos frame = h.absolutePos(c.offset(0, 0, -2));
        player.moveTo(Vec3.atCenterOf(frame).add(0, 1, -3));
        player.setItemInHand(InteractionHand.MAIN_HAND, new ItemStack(Items.ENDER_EYE));
        var hit = new BlockHitResult(Vec3.atCenterOf(frame), Direction.UP, frame, false);
        var event = new PlayerInteractEvent.RightClickBlock(player, InteractionHand.MAIN_HAND, frame, hit);
        MinecraftForge.EVENT_BUS.post(event);
        h.assertTrue(event.isCanceled(), "placing an eye should be blocked while the guardian lives");
        BlockPos portal = PortalData.get(level).find(frame, 16);
        h.assertTrue(portal != null, "portal should be registered");
        PortalData.get(level).markDefeated(portal);
        var event2 = new PlayerInteractEvent.RightClickBlock(player, InteractionHand.MAIN_HAND, frame, hit);
        MinecraftForge.EVENT_BUS.post(event2);
        h.assertFalse(event2.isCanceled(), "after his defeat the portal should accept eyes");
        h.succeed();
    }
}
