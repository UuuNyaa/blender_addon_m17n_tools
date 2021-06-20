# blender_addon_m17n_tools

blender_addon_m17n_tools is a script to assist in the multilingualization (m17n) of add-ons.

## Steps in Multilingualization
1. wrap the string you want to make multilingual with `_(` and `)`
  ```diff
  + from .m17n import _
  +
    class AddSkinHairMesh(bpy.types.Operator):
      bl_idname = 'mmd_uuunyaa_tools.add_skin_hair_mesh'
  -   bl_label = 'Add Skin Hair Mesh'
  -   bl_description = 'Construct a skin hair mesh'
  +   bl_label = _('Add Skin Hair Mesh')
  +   bl_description = _('Construct a skin hair mesh')
      bl_options = {'REGISTER', 'UNDO'}
  ```
2. run the `blender_addon_m17n_tools.py` and output `m17n.py` (any name is ok)
  ```bash
  python BLENDER_ADDON_M17N_TOOLS_DIR/blender_addon_m17n_tools.py generate TARGET_ADDON_SOURCE_DIR -o TARGET_ADDON_SOURCE_DIR/path/to/m17n.py
  ```
3. call `register` function in `m17n.py` at add-on startup
  ```diff
    def register():
  +   from . import m17n
  +   m17n.register()
      bpy.utils.register_class(AddSkinHairMesh)

    def unregister():
      bpy.utils.unregister_class(AddSkinHairMesh)
  +   from . import m17n
  +   m17n.unregister()
  ```
4. edit `m17n.py`
  ```diff
    translation_dict = {
      "en_US": {
        #: TARGET_ADDON_SOURCE_DIR/operators.py:xx
  -     ("*", "Add Skin Hair Mesh"): "Add Skin Hair Mesh",
  +     ("Operator", "Add Skin Hair Mesh"): "Add Skin Hair Mesh",
        #: TARGET_ADDON_SOURCE_DIR/operators.py:xx
        ("*", "Construct a skin hair mesh"): "Construct a skin hair mesh",
      },
  +   "ja_JP": {
  +     #: TARGET_ADDON_SOURCE_DIR/operators.py:xx
  +     ("Operator", "Add Skin Hair Mesh"): "体毛メッシュを追加",
  +     #: TARGET_ADDON_SOURCE_DIR/operators.py:xx
  +     ("*", "Construct a skin hair mesh"): "体毛メッシュを構築",
  +   },
    }
  ```


### Cautions
1. f-string cannot be multilingualized. replace with [str.format](https://docs.python.org/3/library/stdtypes.html#str.format) and use `iface_(`.
2. Multi-line strings are not supported. #1
3. Operator display names context needs to specify the `Operator`.

### How to update `m17n.py` when the code is changed
Run `blender_addon_m17n_tools.py` with `-o` option again to update `m17n.py`.

## See also
- [Application Translations (bpy.app.translations) — Blender Python API](https://docs.blender.org/api/current/bpy.app.translations.html)
- [A reference of specific code editing diffs for multilingualization](https://github.com/UuuNyaa/blender_mmd_uuunyaa_tools/pull/42/files)
