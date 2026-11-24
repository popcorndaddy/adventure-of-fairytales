package com.popcorndaddy.gatekeeper.client;

import com.popcorndaddy.gatekeeper.GatekeeperMod;
import com.popcorndaddy.gatekeeper.entity.GatekeeperEntity;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.model.GeoModel;

public class GatekeeperModel extends GeoModel<GatekeeperEntity> {
    private static final ResourceLocation GEO = new ResourceLocation(GatekeeperMod.MODID, "geo/gatekeeper.geo.json");
    private static final ResourceLocation ANIM = new ResourceLocation(GatekeeperMod.MODID, "animations/gatekeeper.animation.json");
    private static final ResourceLocation TEX = new ResourceLocation(GatekeeperMod.MODID, "textures/entity/gatekeeper.png");
    private static final ResourceLocation TEX_DORMANT = new ResourceLocation(GatekeeperMod.MODID, "textures/entity/gatekeeper_dormant.png");

    @Override
    public ResourceLocation getModelResource(GatekeeperEntity entity) {
        return GEO;
    }

    /** While he sleeps, his eyes, core and fire are dark (the glowmask of the dormant texture omits them). */
    @Override
    public ResourceLocation getTextureResource(GatekeeperEntity entity) {
        return entity.eyesOpen() ? TEX : TEX_DORMANT;
    }

    @Override
    public ResourceLocation getAnimationResource(GatekeeperEntity entity) {
        return ANIM;
    }
}
