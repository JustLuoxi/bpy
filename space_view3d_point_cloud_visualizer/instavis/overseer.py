# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# part of "Point Cloud Visualizer" blender addon
# author: Jakub Uhlik
# (c) 2019, 2020 Jakub Uhlik

import bpy
from bpy.types import Operator
from bpy.props import PointerProperty, BoolProperty, StringProperty, FloatProperty, IntProperty, FloatVectorProperty, EnumProperty, CollectionProperty
from bpy.types import PropertyGroup

from .debug import debug_mode, log
from .mechanist import PCVIVMechanist


class PCVIVOverseer():
    @classmethod
    def init(cls):
        PCVIVMechanist.init()
    
    @classmethod
    def deinit(cls):
        PCVIVMechanist.deinit()
        bpy.app.handlers.load_post.remove(auto_init)
    
    @classmethod
    def apply_settings_psys(cls, source, destinations, ):
        update = False
        apsys = source.particle_system
        apset = apsys.settings
        apcviv = apset.pcv_instavis
        psystems = [mod.particle_system for mod in destinations]
        psettings = [p.settings for p in psystems]
        
        for pset in psettings:
            if(apset is pset):
                continue
            pcviv = pset.pcv_instavis
            pcviv.point_scale = apcviv.point_scale
            pcviv.draw = apcviv.draw
            pcviv.display = apcviv.display
            pcviv.use_origins_only = apcviv.use_origins_only
            update = True
        
        if(update):
            PCVIVMechanist.force_update(with_caches=False, )
    
    @classmethod
    def apply_settings_instances(cls, source, destinations, ):
        changed = []
        aopcviv = source.pcv_instavis
        psystems = [mod.particle_system for mod in destinations]
        psettings = [p.settings for p in psystems]
        cols = [p.instance_collection for p in psettings if p.instance_collection is not None]
        obs = [p.instance_object for p in psettings if p.instance_object is not None]
        
        for col in cols:
            for o in col.objects:
                if(o is source):
                    continue
                ps = o.pcv_instavis
                ps.source = aopcviv.source
                ps.max_points = aopcviv.max_points
                ps.color_source = aopcviv.color_source
                ps.color_constant = aopcviv.color_constant
                ps.use_face_area = aopcviv.use_face_area
                ps.use_material_factors = aopcviv.use_material_factors
                ps.point_size = aopcviv.point_size
                ps.point_size_f = aopcviv.point_size_f
                changed.append(o)
        
        for o in obs:
            if(o is source):
                continue
            ps = o.pcv_instavis
            ps.source = aopcviv.source
            ps.max_points = aopcviv.max_points
            ps.color_source = aopcviv.color_source
            ps.color_constant = aopcviv.color_constant
            ps.use_face_area = aopcviv.use_face_area
            ps.use_material_factors = aopcviv.use_material_factors
            ps.point_size = aopcviv.point_size
            ps.point_size_f = aopcviv.point_size_f
            changed.append(o)
        
        for o in changed:
            PCVIVMechanist.invalidate_object_cache(o.name)
    
    # @classmethod
    # def set_draw(cls, destinations, draw, ):
    #     addon_prefs = bpy.context.preferences.addons["Scatter"].preferences
    #     addon_prefs.A_instavis_enabled = True
    #
    #     psettings = [mod.particle_system.settings for mod in destinations]
    #     for pset in psettings:
    #         pset.pcv_instavis.draw = draw
    
    @classmethod
    def set_draw_type(cls, destinations, type, ):
        psettings = [mod.particle_system.settings for mod in destinations]
        for pset in psettings:
            if(type == 'ORIGINS'):
                pset.pcv_instavis.use_origins_only = True
            else:
                pset.pcv_instavis.use_origins_only = False
        PCVIVMechanist.force_update(with_caches=True, )
    
    psys_prop_map = {
        'point_scale': 'point_scale',
        'point_percentage': 'display',
    }
    
    @classmethod
    def apply_psys_prop(cls, context, destinations, prop_name, ):
        pcviv_master = context.scene.pcviv_master_properties
        try:
            v = pcviv_master[prop_name]
        except Exception as e:
            v = pcviv_master.bl_rna.properties[prop_name].default
        n = cls.psys_prop_map[prop_name]
        psettings = [mod.particle_system.settings for mod in destinations]
        for pset in psettings:
            pset.pcv_instavis[n] = v
        PCVIVMechanist.force_update(with_caches=False, )


class SCUtils():
    @classmethod
    def collect(cls, scene=False, ):
        prefix = "SCATTER"
        sc_mods = []
        if(scene):
            sc_mods = [m for o in bpy.context.scene.objects for m in o.modifiers if m.name.startswith(prefix)]
        else:
            o = bpy.context.scene.C_Slots_settings.Terrain_pointer
            sc_mods = [m for m in o.modifiers if m.name.startswith(prefix)]
        user_sel = [m for m in sc_mods if m.particle_system.settings.scatter_ui.is_selected]
        last_sel = None
        if(len(user_sel)):
            ts = [(m.particle_system.settings.scatter_ui.is_selected_time, i, ) for i, m in enumerate(user_sel)]
            ts.sort()
            tsl, tsli = ts[len(ts) - 1]
            if(tsl > 0.0):
                last_sel = user_sel[tsli]
        
        return tuple(sc_mods), tuple(user_sel), last_sel


def pcviv_draw_sc_ui_obsolete(context, uilayout, ):
    addon_prefs = bpy.context.preferences.addons["Scatter"].preferences
    terrain = bpy.context.scene.C_Slots_settings.Terrain_pointer
    scatter_particles, scatter_selected, last_sel = SCUtils.collect()
    
    # big enable button
    tab = uilayout.box()
    r = tab.row()
    r.prop(addon_prefs, 'A_instavis_enabled', toggle=True, )
    r.scale_y = 1.5
    
    # last selected particles
    tab = uilayout.box()
    h = tab.box()
    h.operator("scatter.general_panel_toggle", emboss=False, text='Particle Visualization Options', icon='PARTICLES', ).pref = "addon_prefs.A_instavis_controls_is_open"
    if(addon_prefs.A_instavis_controls_is_open):
        if(last_sel is not None):
            pset_pcviv = last_sel.particle_system.settings.pcv_instavis
            cc = tab.column()
            cc.label(text='{} > {} > {}'.format(terrain.name, last_sel.particle_system.name, last_sel.particle_system.settings.name))
            cc.prop(pset_pcviv, 'display')
            r = cc.row()
            r.prop(pset_pcviv, 'point_scale')
            if(pset_pcviv.use_origins_only):
                r.enabled = False
            r = cc.row()
            r.prop(pset_pcviv, 'use_origins_only')
            ccc = r.column(align=True)
            pcviv_prefs = context.scene.pcv_instavis
            if(pcviv_prefs.quality == 'BASIC'):
                ccc.prop(pcviv_prefs, 'origins_point_size')
            else:
                ccc.prop(pcviv_prefs, 'origins_point_size_f')
            if(not pset_pcviv.use_origins_only):
                ccc.enabled = False
        else:
            cc = tab.column()
            cc.label(text="No Selected System(s)", icon='ERROR', )
        
        tab.separator()
        
        c = tab.column()
        r = c.row(align=True)
        r.label(text="{}:".format(addon_prefs.bl_rna.properties['A_instavis_influence'].name))
        r.prop(addon_prefs, 'A_instavis_influence', expand=True, )
        t = "{} to {}".format(PCVIV_OT_sc_apply_settings_psys.bl_label, addon_prefs.A_instavis_influence, )
        if(addon_prefs.A_instavis_influence in ('SCENE', )):
            t = "{} [Batch]".format(t)
        r = tab.row()
        r.operator('pcviv.sc_apply_settings_psys', text=t, )
    
    # last selected particles instanced objects
    tab = uilayout.box()
    h = tab.box()
    h.operator("scatter.general_panel_toggle", emboss=False, text='Instance Visualization Options', icon='OUTLINER_OB_GROUP_INSTANCE', ).pref = "addon_prefs.A_instavis_instances_is_open"
    if(addon_prefs.A_instavis_instances_is_open):
        if(last_sel is not None):
            c = tab.column()
            pset = last_sel.particle_system.settings
            if(pset.render_type == 'COLLECTION' and pset.instance_collection is not None):
                c.label(text='{} > {}'.format(last_sel.particle_system.settings.name, pset.instance_collection.name))
                
                col = pset.instance_collection
                pcvcol = col.pcv_instavis
                c.template_list("PCVIV_UL_instances", "", col, "objects", pcvcol, "active_index", rows=5, )
                
                co = col.objects[col.objects.keys()[pcvcol.active_index]]
                pcvco = co.pcv_instavis
                
                c.label(text='Base Object "{}" Settings:'.format(co.name), )
                
                pcviv_prefs = context.scene.pcv_instavis
                if(pcviv_prefs.quality == 'BASIC'):
                    c.prop(pcvco, 'point_size')
                else:
                    c.prop(pcvco, 'point_size_f')
                
                c.prop(pcvco, 'source', )
                c.prop(pcvco, 'max_points')
                
                if(pcvco.source == 'VERTICES'):
                    r = c.row()
                    r.prop(pcvco, 'color_constant', )
                else:
                    c.prop(pcvco, 'color_source', )
                    if(pcvco.color_source == 'CONSTANT'):
                        r = c.row()
                        r.prop(pcvco, 'color_constant', )
                    else:
                        c.prop(pcvco, 'use_face_area')
                        c.prop(pcvco, 'use_material_factors')
                
                if(pcvco.use_material_factors):
                    b = c.box()
                    cc = b.column(align=True)
                    for slot in co.material_slots:
                        if(slot.material is not None):
                            cc.prop(slot.material.pcv_instavis, 'factor', text=slot.material.name)
            elif(pset.render_type == 'OBJECT' and pset.instance_object is not None):
                c.label(text='{} > {}'.format(last_sel.particle_system.settings.name, pset.instance_object.name))
                
                co = pset.instance_object
                b = c.box()
                b.label(text=co.name, icon='OBJECT_DATA', )
                
                c.label(text='Base Object "{}" Settings:'.format(co.name), )
                
                pcvco = co.pcv_instavis
                
                pcviv_prefs = context.scene.pcv_instavis
                if(pcviv_prefs.quality == 'BASIC'):
                    c.prop(pcvco, 'point_size')
                else:
                    c.prop(pcvco, 'point_size_f')
                
                c.prop(pcvco, 'source', )
                c.prop(pcvco, 'max_points')
                
                if(pcvco.source == 'VERTICES'):
                    r = c.row()
                    r.prop(pcvco, 'color_constant', )
                else:
                    c.prop(pcvco, 'color_source', )
                    if(pcvco.color_source == 'CONSTANT'):
                        r = c.row()
                        r.prop(pcvco, 'color_constant', )
                    else:
                        c.prop(pcvco, 'use_face_area')
                        c.prop(pcvco, 'use_material_factors')
                
                if(pcvco.use_material_factors):
                    b = c.box()
                    cc = b.column(align=True)
                    for slot in co.material_slots:
                        if(slot.material is not None):
                            cc.prop(slot.material.pcv_instavis, 'factor', text=slot.material.name)
            else:
                c.label(text="No collection/object found.", icon='ERROR', )
        else:
            cc = tab.column()
            cc.label(text="No Selected System(s)", icon='ERROR', )
        
        tab.separator()
        
        c = tab.column()
        r = c.row(align=True)
        r.label(text="{}:".format(addon_prefs.bl_rna.properties['A_instavis_influence_instances'].name))
        r.prop(addon_prefs, 'A_instavis_influence_instances', expand=True, )
        t = "{} to {}".format(PCVIV_OT_sc_apply_settings_instances.bl_label, addon_prefs.A_instavis_influence_instances, )
        if(addon_prefs.A_instavis_influence_instances in ('SCENE', 'SELECTED', )):
            t = "{} [Batch]".format(t)
        r = tab.row()
        r.operator('pcviv.sc_apply_settings_instances', text=t, )
    
    # global settings
    tab = uilayout.box()
    h = tab.box()
    h.operator("scatter.general_panel_toggle", emboss=False, text="Global Settings", icon='SETTINGS', ).pref = "addon_prefs.A_instavis_global_is_open"
    if(addon_prefs.A_instavis_global_is_open):
        c = tab.column()
        pcviv_prefs = context.scene.pcv_instavis
        c.prop(pcviv_prefs, 'quality')
        c.prop(pcviv_prefs, 'update_method')
        c.separator()
        c.prop(pcviv_prefs, 'use_exit_display')
        cc = c.column()
        cc.prop(pcviv_prefs, 'exit_object_display_type')
        cc.prop(pcviv_prefs, 'exit_psys_display_method')
        cc.enabled = pcviv_prefs.use_exit_display
        c.separator()
        c.label(text="Auto Switch To Origins Only:")
        c.prop(pcviv_prefs, 'switch_origins_only', text='Enabled', )
        c.prop(pcviv_prefs, 'switch_origins_only_threshold')


def pcviv_draw_sc_ui(context, uilayout, ):
    addon_prefs = bpy.context.preferences.addons["Scatter"].preferences
    terrain = bpy.context.scene.C_Slots_settings.Terrain_pointer
    scatter_particles, scatter_selected, last_sel = SCUtils.collect()
    
    tab = uilayout.box()
    c = tab.column()
    c.prop(addon_prefs, 'A_instavis_enabled', toggle=True, )
    c.separator()
    
    c = tab.column()
    r = c.row(align=True)
    r.label(text="{}:".format(addon_prefs.bl_rna.properties['A_instavis_influence'].name))
    r.prop(addon_prefs, 'A_instavis_influence', expand=True, )
    c.separator()
    
    cc = c.column(align=True)
    # cc.operator('pcviv.sc_draw', text="Start", ).draw = True
    # cc.operator('pcviv.sc_draw', text="Stop", ).draw = False
    # cc.separator()
    cc.operator('pcviv.sc_draw_type', text="Full", ).type = 'FULL'
    
    pcviv_master = context.scene.pcviv_master_properties
    r = cc.row(align=True, )
    r.prop(pcviv_master, 'point_scale')
    r.operator('pcviv.sc_apply_psys_prop', ).prop_name = 'point_scale'
    r = cc.row(align=True, )
    r.prop(pcviv_master, 'point_percentage')
    r.operator('pcviv.sc_apply_psys_prop', ).prop_name = 'point_percentage'
    
    cc.separator()
    cc.operator('pcviv.sc_draw_type', text="Origins", ).type = 'ORIGINS'
    
    if(addon_prefs.A_instavis_influence == 'SELECTED'):
        if(not len(scatter_selected)):
            cc.enabled = False
    

class PCVIV_OT_sc_apply_settings_psys(Operator):
    bl_idname = "pcviv.sc_apply_settings_psys"
    bl_label = "Apply Settings"
    bl_description = "Apply settings from active to selected or all in scene"
    
    @classmethod
    def poll(cls, context):
        if(PCVIVMechanist.initialized):
            addon_prefs = bpy.context.preferences.addons["Scatter"].preferences
            scatter_particles, scatter_selected, last_sel = SCUtils.collect()
            if(len(scatter_selected) > 0):
                if(addon_prefs.A_instavis_influence in ('SELECTED', )):
                    if(len(scatter_selected) <= 1):
                        return False
                return True
        return False
    
    def execute(self, context):
        scatter_particles, scatter_selected, last_sel = SCUtils.collect()
        addon_prefs = bpy.context.preferences.addons["Scatter"].preferences
        if(addon_prefs.A_instavis_influence == 'SCENE'):
            destinations = scatter_particles
        else:
            destinations = scatter_selected
        if(last_sel is not None):
            PCVIVOverseer.apply_settings_psys(last_sel, destinations, )
        return {'FINISHED'}


class PCVIV_OT_sc_apply_settings_instances(Operator):
    bl_idname = "pcviv.sc_apply_settings_instances"
    bl_label = "Apply Settings"
    bl_description = "Apply settings from active to selected or all in scene"
    
    @classmethod
    def poll(cls, context):
        if(PCVIVMechanist.initialized):
            scatter_particles, scatter_selected, last_sel = SCUtils.collect()
            if(len(scatter_selected) > 0):
                return True
        return False
    
    def execute(self, context):
        scatter_particles, scatter_selected, last_sel = SCUtils.collect()
        addon_prefs = bpy.context.preferences.addons["Scatter"].preferences
        if(addon_prefs.A_instavis_influence == 'SCENE'):
            destinations = scatter_particles
        elif(addon_prefs.A_instavis_influence == 'SELECTED'):
            destinations = scatter_selected
        else:
            destinations = last_sel
        pset = last_sel.particle_system.settings
        if(pset.render_type == 'COLLECTION' and pset.instance_collection is not None):
            col = pset.instance_collection
            pcvcol = col.pcv_instavis
            source = col.objects[col.objects.keys()[pcvcol.active_index]]
        elif(pset.render_type == 'OBJECT' and pset.instance_object is not None):
            source.pset.instance_object
        if(source is not None):
            PCVIVOverseer.apply_settings_instances(source, destinations, )
        return {'FINISHED'}


'''
class PCVIV_OT_sc_draw(Operator):
    bl_idname = "pcviv.sc_draw"
    bl_label = "Draw"
    bl_description = ""
    
    draw: BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE', }, )
    
    @classmethod
    def poll(cls, context):
        if(PCVIVMechanist.initialized):
            addon_prefs = bpy.context.preferences.addons["Scatter"].preferences
            scatter_particles, scatter_selected, last_sel = SCUtils.collect()
            if(len(scatter_selected) > 0):
                # if(addon_prefs.A_instavis_influence in ('SELECTED', )):
                #     if(len(scatter_selected) <= 1):
                #         return False
                return True
        return False
    
    def execute(self, context):
        scatter_particles, scatter_selected, last_sel = SCUtils.collect()
        addon_prefs = bpy.context.preferences.addons["Scatter"].preferences
        if(addon_prefs.A_instavis_influence == 'SCENE'):
            destinations = scatter_particles
        else:
            destinations = scatter_selected
        PCVIVOverseer.set_draw(destinations, self.draw, )
        return {'FINISHED'}
'''


class PCVIV_OT_sc_draw_type(Operator):
    bl_idname = "pcviv.sc_draw_type"
    bl_label = "Type"
    bl_description = ""
    
    type: EnumProperty(items=[('FULL', '', "", ), ('ORIGINS', '', "", ), ], default='FULL', options={'HIDDEN', 'SKIP_SAVE', }, )
    
    @classmethod
    def poll(cls, context):
        if(PCVIVMechanist.initialized):
            addon_prefs = bpy.context.preferences.addons["Scatter"].preferences
            if(addon_prefs.A_instavis_influence in ('SCENE', )):
                return True
            scatter_particles, scatter_selected, last_sel = SCUtils.collect()
            if(len(scatter_selected) > 0):
                # if(addon_prefs.A_instavis_influence in ('SELECTED', )):
                #     if(len(scatter_selected) <= 1):
                #         return False
                return True
        return False
    
    def execute(self, context):
        scatter_particles, scatter_selected, last_sel = SCUtils.collect()
        addon_prefs = bpy.context.preferences.addons["Scatter"].preferences
        if(addon_prefs.A_instavis_influence == 'SCENE'):
            destinations = scatter_particles
        else:
            destinations = scatter_selected
        PCVIVOverseer.set_draw_type(destinations, self.type, )
        return {'FINISHED'}


class PCVIV_OT_sc_apply_psys_prop(Operator):
    bl_idname = "pcviv.sc_apply_psys_prop"
    bl_label = "Apply"
    bl_description = ""
    
    prop_name: StringProperty(default='', options={'HIDDEN', 'SKIP_SAVE', }, )
    
    @classmethod
    def poll(cls, context):
        if(PCVIVMechanist.initialized):
            addon_prefs = bpy.context.preferences.addons["Scatter"].preferences
            if(addon_prefs.A_instavis_influence in ('SCENE', )):
                return True
            scatter_particles, scatter_selected, last_sel = SCUtils.collect()
            if(len(scatter_selected) > 0):
                # if(addon_prefs.A_instavis_influence in ('SELECTED', )):
                #     if(len(scatter_selected) <= 1):
                #         return False
                return True
        return False
    
    def execute(self, context):
        scatter_particles, scatter_selected, last_sel = SCUtils.collect()
        addon_prefs = bpy.context.preferences.addons["Scatter"].preferences
        if(addon_prefs.A_instavis_influence == 'SCENE'):
            destinations = scatter_particles
        else:
            destinations = scatter_selected
        PCVIVOverseer.apply_psys_prop(context, destinations, self.prop_name, )
        return {'FINISHED'}


class PCVIV_master_properties(PropertyGroup):
    point_scale: FloatProperty(name="Point Scale", default=1.0, min=0.001, max=10.0, precision=6, description="Adjust point size of all points", )
    point_percentage: FloatProperty(name="Point Percentage", default=100.0, min=0.0, max=100.0, precision=0, subtype='PERCENTAGE', description="Adjust percentage of displayed points", )
    origins_point_size: IntProperty(name="Size (Basic Shader)", default=6, min=1, max=10, subtype='PIXEL', description="Point size", )
    origins_point_size_f: FloatProperty(name="Size (Rich Shader)", default=0.05, min=0.001, max=1.0, precision=6, description="Point size", )
    
    @classmethod
    def register(cls):
        bpy.types.Scene.pcviv_master_properties = PointerProperty(type=cls)
    
    @classmethod
    def unregister(cls):
        del bpy.types.Scene.pcviv_master_properties


@bpy.app.handlers.persistent
def auto_init(undefined):
    PCVIVOverseer.init()


# auto initialize, this will be called once when blend file is loaded, even startup file
bpy.app.handlers.load_post.append(auto_init)

classes = (PCVIV_OT_sc_apply_settings_psys, PCVIV_OT_sc_apply_settings_instances,
           PCVIV_master_properties,
           # PCVIV_OT_sc_draw,
           PCVIV_OT_sc_draw_type,
           PCVIV_OT_sc_apply_psys_prop,
           )
classes_debug = ()