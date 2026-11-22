package com.popcorndaddy.gatekeeper.portal;

import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtUtils;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

import javax.annotation.Nullable;
import java.util.HashMap;
import java.util.Map;

/** Per-dimension record of every End portal the Gatekeeper guards: false = still sealed, true = guardian defeated. */
public class PortalData extends SavedData {
    private static final String NAME = "aof_gatekeeper_portals";
    private final Map<BlockPos, Boolean> portals = new HashMap<>();

    public static PortalData get(ServerLevel level) {
        return level.getDataStorage().computeIfAbsent(PortalData::load, PortalData::new, NAME);
    }

    public static PortalData load(CompoundTag tag) {
        PortalData d = new PortalData();
        ListTag list = tag.getList("Portals", Tag.TAG_COMPOUND);
        for (int i = 0; i < list.size(); i++) {
            CompoundTag c = list.getCompound(i);
            d.portals.put(NbtUtils.readBlockPos(c.getCompound("Pos")), c.getBoolean("Defeated"));
        }
        return d;
    }

    @Override
    public CompoundTag save(CompoundTag tag) {
        ListTag list = new ListTag();
        portals.forEach((pos, defeated) -> {
            CompoundTag c = new CompoundTag();
            c.put("Pos", NbtUtils.writeBlockPos(pos));
            c.putBoolean("Defeated", defeated);
            list.add(c);
        });
        tag.put("Portals", list);
        return tag;
    }

    /** The registered portal within `radius` blocks of `pos`, if any. */
    @Nullable
    public BlockPos find(BlockPos pos, int radius) {
        for (BlockPos p : portals.keySet()) {
            if (p.distManhattan(pos) <= radius * 2 && p.closerThan(pos, radius)) return p;
        }
        return null;
    }

    public boolean isDefeated(BlockPos portal) {
        return Boolean.TRUE.equals(portals.get(portal));
    }

    public void register(BlockPos portal) {
        portals.putIfAbsent(portal, false);
        setDirty();
    }

    public void markDefeated(BlockPos portal) {
        portals.put(portal, true);
        setDirty();
    }
}
