package com.popcorndaddy.gatekeeper;

import com.popcorndaddy.gatekeeper.entity.GatekeeperEntity;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.item.CreativeModeTabs;
import net.minecraft.world.item.Item;
import net.minecraftforge.common.ForgeSpawnEggItem;
import net.minecraftforge.event.BuildCreativeModeTabContentsEvent;
import net.minecraftforge.event.entity.EntityAttributeCreationEvent;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

@Mod(GatekeeperMod.MODID)
public class GatekeeperMod {
    public static final String MODID = "aof_gatekeeper";

    public static final DeferredRegister<EntityType<?>> ENTITIES = DeferredRegister.create(ForgeRegistries.ENTITY_TYPES, MODID);
    public static final DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, MODID);
    public static final DeferredRegister<SoundEvent> SOUNDS = DeferredRegister.create(ForgeRegistries.SOUND_EVENTS, MODID);

    // The model is ~8.4 blocks tall in Blender; it is rendered at 0.72 scale, so the hitbox is ~6 blocks tall.
    public static final RegistryObject<EntityType<GatekeeperEntity>> GATEKEEPER = ENTITIES.register("gatekeeper",
            () -> EntityType.Builder.of(GatekeeperEntity::new, MobCategory.MONSTER)
                    .sized(3.2f, 6.0f).fireImmune().clientTrackingRange(16).updateInterval(2)
                    .build(new ResourceLocation(MODID, "gatekeeper").toString()));

    public static final RegistryObject<Item> GATEKEEPER_SPAWN_EGG = ITEMS.register("gatekeeper_spawn_egg",
            () -> new ForgeSpawnEggItem(GATEKEEPER, 0x140b1f, 0xb04cff, new Item.Properties()));

    public static final RegistryObject<SoundEvent> SND_AMBIENT = sound("gatekeeper.ambient");
    public static final RegistryObject<SoundEvent> SND_PULSE = sound("gatekeeper.pulse");
    public static final RegistryObject<SoundEvent> SND_SHRIEK = sound("gatekeeper.shriek");
    public static final RegistryObject<SoundEvent> SND_STEP = sound("gatekeeper.step");
    public static final RegistryObject<SoundEvent> SND_IMPACT = sound("gatekeeper.impact");
    public static final RegistryObject<SoundEvent> SND_WHOOSH = sound("gatekeeper.whoosh");
    public static final RegistryObject<SoundEvent> SND_DRAG = sound("gatekeeper.drag");
    public static final RegistryObject<SoundEvent> SND_EYES = sound("gatekeeper.eyes_open");
    public static final RegistryObject<SoundEvent> SND_PORTAL = sound("gatekeeper.portal_flicker");

    private static RegistryObject<SoundEvent> sound(String name) {
        return SOUNDS.register(name, () -> SoundEvent.createVariableRangeEvent(new ResourceLocation(MODID, name)));
    }

    public GatekeeperMod() {
        IEventBus bus = FMLJavaModLoadingContext.get().getModEventBus();
        ENTITIES.register(bus);
        ITEMS.register(bus);
        SOUNDS.register(bus);
        bus.addListener(this::attributes);
        bus.addListener(this::creativeTabs);
    }

    private void attributes(EntityAttributeCreationEvent event) {
        event.put(GATEKEEPER.get(), GatekeeperEntity.createAttributes().build());
    }

    private void creativeTabs(BuildCreativeModeTabContentsEvent event) {
        if (event.getTabKey() == CreativeModeTabs.SPAWN_EGGS) {
            event.accept(GATEKEEPER_SPAWN_EGG);
        }
    }
}
