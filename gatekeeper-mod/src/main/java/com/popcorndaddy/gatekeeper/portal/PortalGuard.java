package com.popcorndaddy.gatekeeper.portal;

import com.popcorndaddy.gatekeeper.GatekeeperMod;
import com.popcorndaddy.gatekeeper.entity.GatekeeperEntity;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.registries.ForgeRegistries;

import javax.annotation.Nullable;
import java.util.Set;

/**
 * The Gatekeeper guards every End portal (vanilla stronghold frames and End Remastered's ancient portal frames).
 * When a player first comes near one, a dormant Gatekeeper appears in front of it. Until he is defeated the portal
 * is sealed: no eye can be placed in its frames.
 */
@Mod.EventBusSubscriber(modid = GatekeeperMod.MODID)
public class PortalGuard {
    private static final Set<ResourceLocation> FRAMES = Set.of(
            new ResourceLocation("minecraft", "end_portal_frame"),
            new ResourceLocation("endrem", "ancient_portal_frame"));
    private static final int SCAN_XZ = 14, SCAN_Y = 7, PORTAL_RADIUS = 16;

    static boolean isFrame(BlockState state) {
        ResourceLocation id = ForgeRegistries.BLOCKS.getKey(state.getBlock());
        return id != null && FRAMES.contains(id);
    }

    /** Centre of the portal frame cluster near `around`, or null if there is none. */
    @Nullable
    static BlockPos findPortal(ServerLevel level, BlockPos around) {
        long sx = 0, sy = 0, sz = 0;
        int n = 0;
        BlockPos.MutableBlockPos m = new BlockPos.MutableBlockPos();
        for (int y = -SCAN_Y; y <= SCAN_Y; y++) {
            for (int x = -SCAN_XZ; x <= SCAN_XZ; x++) {
                for (int z = -SCAN_XZ; z <= SCAN_XZ; z++) {
                    m.set(around.getX() + x, around.getY() + y, around.getZ() + z);
                    if (!level.isLoaded(m)) continue;
                    if (isFrame(level.getBlockState(m))) {
                        sx += m.getX(); sy += m.getY(); sz += m.getZ(); n++;
                    }
                }
            }
        }
        if (n < 4) return null;                      // a real portal ring, not a lone frame
        return new BlockPos((int) Math.floorDiv(sx, n), (int) Math.floorDiv(sy, n), (int) Math.floorDiv(sz, n));
    }

    @SubscribeEvent
    public static void onPlayerTick(TickEvent.PlayerTickEvent event) {
        if (event.phase != TickEvent.Phase.END || event.player.level().isClientSide) return;
        Player player = event.player;
        if (player.tickCount % 40 != 0 || player.isSpectator()) return;
        ServerLevel level = (ServerLevel) player.level();
        PortalData data = PortalData.get(level);

        BlockPos known = data.find(player.blockPosition(), PORTAL_RADIUS + 8);
        BlockPos portal = known != null ? known : findPortal(level, player.blockPosition());
        if (portal == null) return;
        if (known == null) data.register(portal);
        if (data.isDefeated(portal)) return;

        // is his guardian already here?
        boolean present = !level.getEntitiesOfClass(GatekeeperEntity.class, new AABB(portal).inflate(40),
                g -> portal.equals(g.guardedPortal()) || g.guardedPortal() == null).isEmpty();
        if (present || player.isCreative()) return;

        // stand him on the floor between the portal and the player, facing the player
        Vec3 toPlayer = player.position().subtract(Vec3.atCenterOf(portal));
        Vec3 flat = new Vec3(toPlayer.x, 0, toPlayer.z);
        Vec3 dir = flat.lengthSqr() > 0.01 ? flat.normalize() : new Vec3(0, 0, 1);
        Vec3 spot = Vec3.atCenterOf(portal).add(dir.scale(5.0));
        BlockPos pos = groundBelow(level, BlockPos.containing(spot));
        GatekeeperEntity.spawnGuardian(level, pos, player.position(), portal);
        level.playSound(null, portal, GatekeeperMod.SND_PORTAL.get(), net.minecraft.sounds.SoundSource.HOSTILE, 3.0f, 0.8f);
        player.displayClientMessage(Component.translatable("message.aof_gatekeeper.guardian_appears"), true);
    }

    private static BlockPos groundBelow(ServerLevel level, BlockPos start) {
        BlockPos.MutableBlockPos m = start.mutable();
        for (int i = 0; i < 12 && level.getBlockState(m.below()).isAir(); i++) m.move(0, -1, 0);
        for (int i = 0; i < 6 && !level.getBlockState(m).isAir(); i++) m.move(0, 1, 0);
        return m.immutable();
    }

    /** The seal: while the guardian lives, nothing can be placed into the portal's frames. */
    @SubscribeEvent
    public static void onRightClickBlock(PlayerInteractEvent.RightClickBlock event) {
        if (!(event.getLevel() instanceof ServerLevel level)) {
            if (isFrame(event.getLevel().getBlockState(event.getPos())) && event.getEntity().getItemInHand(event.getHand()).isEmpty()) return;
            return;
        }
        if (!isFrame(level.getBlockState(event.getPos()))) return;
        if (event.getEntity().isCreative()) return;
        PortalData data = PortalData.get(level);
        BlockPos portal = data.find(event.getPos(), PORTAL_RADIUS);
        if (portal == null) {
            portal = findPortal(level, event.getPos());
            if (portal == null) return;
            data.register(portal);
        }
        if (data.isDefeated(portal)) return;
        event.setCanceled(true);
        event.getEntity().displayClientMessage(Component.translatable("message.aof_gatekeeper.sealed"), true);
        level.playSound(null, event.getPos(), GatekeeperMod.SND_PULSE.get(), net.minecraft.sounds.SoundSource.BLOCKS, 1.0f, 0.6f);
    }

    @SuppressWarnings("unused")
    private static Block block(String id) { return ForgeRegistries.BLOCKS.getValue(new ResourceLocation(id)); }
}
