package com.aof.gateknight;

import com.aof.gateknight.entity.GateKnightEntity;
import net.minecraft.resources.ResourceLocation;
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

@Mod(GateKnightMod.MODID)
public class GateKnightMod {
    public static final String MODID = "aof_gateknight";

    public static final DeferredRegister<EntityType<?>> ENTITIES = DeferredRegister.create(ForgeRegistries.ENTITY_TYPES, MODID);
    public static final DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, MODID);

    /** The model is ~8.4 blocks tall at scale 1. */
    public static final RegistryObject<EntityType<GateKnightEntity>> GATE_KNIGHT = ENTITIES.register("gate_knight",
            () -> EntityType.Builder.of(GateKnightEntity::new, MobCategory.MONSTER)
                    .sized(2.6f, 8.4f).fireImmune().clientTrackingRange(16).updateInterval(2)
                    .build(new ResourceLocation(MODID, "gate_knight").toString()));

    public static final RegistryObject<Item> GATE_KNIGHT_SPAWN_EGG = ITEMS.register("gate_knight_spawn_egg",
            () -> new ForgeSpawnEggItem(GATE_KNIGHT, 0x141018, 0xA040FF, new Item.Properties()));

    public GateKnightMod() {
        IEventBus bus = FMLJavaModLoadingContext.get().getModEventBus();
        ENTITIES.register(bus);
        ITEMS.register(bus);
        bus.addListener(this::attributes);
        bus.addListener(this::creativeTabs);
    }

    private void attributes(EntityAttributeCreationEvent event) {
        event.put(GATE_KNIGHT.get(), GateKnightEntity.createAttributes().build());
    }

    private void creativeTabs(BuildCreativeModeTabContentsEvent event) {
        if (event.getTabKey() == CreativeModeTabs.SPAWN_EGGS) event.accept(GATE_KNIGHT_SPAWN_EGG);
    }
}
