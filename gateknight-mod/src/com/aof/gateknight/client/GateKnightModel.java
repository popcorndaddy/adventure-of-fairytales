package com.aof.gateknight.client;

import com.aof.gateknight.GateKnightMod;
import com.aof.gateknight.entity.GateKnightEntity;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.model.GeoModel;

public class GateKnightModel extends GeoModel<GateKnightEntity> {
    private static final ResourceLocation GEO = new ResourceLocation(GateKnightMod.MODID, "geo/gate_knight.geo.json");
    private static final ResourceLocation ANIM = new ResourceLocation(GateKnightMod.MODID, "animations/gate_knight.animation.json");
    private static final ResourceLocation TEX = new ResourceLocation(GateKnightMod.MODID, "textures/entity/gate_knight.png");
    /** same albedo; its _glowmask burns brighter once he has roared */
    private static final ResourceLocation TEX_ENRAGED = new ResourceLocation(GateKnightMod.MODID, "textures/entity/gate_knight_enraged.png");

    @Override public ResourceLocation getModelResource(GateKnightEntity e) { return GEO; }
    @Override public ResourceLocation getTextureResource(GateKnightEntity e) { return e.enraged() ? TEX_ENRAGED : TEX; }
    @Override public ResourceLocation getAnimationResource(GateKnightEntity e) { return ANIM; }
}
