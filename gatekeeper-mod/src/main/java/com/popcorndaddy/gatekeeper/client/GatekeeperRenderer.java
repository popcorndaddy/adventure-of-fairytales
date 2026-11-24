package com.popcorndaddy.gatekeeper.client;

import com.popcorndaddy.gatekeeper.GatekeeperMod;
import com.popcorndaddy.gatekeeper.entity.GatekeeperEntity;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import software.bernie.geckolib.renderer.GeoEntityRenderer;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

public class GatekeeperRenderer extends GeoEntityRenderer<GatekeeperEntity> {
    public GatekeeperRenderer(EntityRendererProvider.Context ctx) {
        super(ctx, new GatekeeperModel());
        this.withScale(0.72f);                       // ~6 blocks tall in game
        this.shadowRadius = 2.2f;
        this.addRenderLayer(new AutoGlowingGeoLayer<>(this));   // eyes, core, runes, fire glow in the dark
    }

    @Override
    protected float getDeathMaxRotation(GatekeeperEntity entity) {
        return 0f;                                   // he collapses with his own death animation, not the vanilla tip-over
    }

    @Mod.EventBusSubscriber(modid = GatekeeperMod.MODID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
    public static class Registration {
        @SubscribeEvent
        public static void registerRenderers(EntityRenderersEvent.RegisterRenderers event) {
            event.registerEntityRenderer(GatekeeperMod.GATEKEEPER.get(), GatekeeperRenderer::new);
        }
    }
}
