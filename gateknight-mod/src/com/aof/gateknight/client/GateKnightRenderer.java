package com.aof.gateknight.client;

import com.aof.gateknight.GateKnightMod;
import com.aof.gateknight.entity.GateKnightEntity;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import software.bernie.geckolib.renderer.GeoEntityRenderer;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

public class GateKnightRenderer extends GeoEntityRenderer<GateKnightEntity> {
    public GateKnightRenderer(EntityRendererProvider.Context ctx) {
        super(ctx, new GateKnightModel());
        this.shadowRadius = 1.6f;
        this.addRenderLayer(new AutoGlowingGeoLayer<>(this));   // purple trim, runes and visor glow in the dark
    }

    @Override
    protected float getDeathMaxRotation(GateKnightEntity entity) {
        return 0f;                                               // he kneels on his sword in his death animation instead of tipping over
    }

    @Mod.EventBusSubscriber(modid = GateKnightMod.MODID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
    public static class Registration {
        @SubscribeEvent
        public static void registerRenderers(EntityRenderersEvent.RegisterRenderers event) {
            event.registerEntityRenderer(GateKnightMod.GATE_KNIGHT.get(), GateKnightRenderer::new);
        }
    }
}
