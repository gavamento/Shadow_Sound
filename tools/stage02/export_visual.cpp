//====================================================================================
//                          export_visual.cpp
//  三校/ 秋田蓮音                                                          09/12/2026
//                    静的 FBX のノード階層を、エンジンと同じ ufbx 設定で読んで JSON に書く
//====================================================================================
// 使い方: export_visual.exe input.fbx output.json
//
// ★エンジン (C:\HAL\MyEngin\tools\stage01\export_prefab_visual.cpp) の写し。違いは 2 つ:
//   (1) AssetID のハッシュをここで計算しない。サブアセットのキーは M74a 以降
//       "guid://<FBX の .meta の guid>#mesh<element_id>#part<n>" / "#mat<element_id>" で、
//       guid は .meta を持つ build_collision.py 側が知っている。ここは接尾辞だけを書く
//   (2) ルート名は呼び出し側が付ける (ここではノードだけ)
// ★ufbx の読み込み設定は FbxLoader.cpp の MakeOpts と 1 つずつ同じにすること。
//   geometry_transform_handling を変えると helper ノード ("geo") の有無が変わり、
//   階層も element_id の並びもずれて、描画が黙って消える
#include "ufbx/ufbx.h"
#include "nlohmann/json.hpp"
#include <fstream>
#include <functional>
#include <iostream>
#include <stdexcept>

using nlohmann::json;

int main(int argc, char** argv)
{
    try {
        if (argc != 3) throw std::runtime_error("usage: export_visual input.fbx output.json");
        ufbx_load_opts opts = {};
        opts.target_axes = ufbx_axes_left_handed_y_up;
        opts.handedness_conversion_axis = UFBX_MIRROR_AXIS_Z;
        opts.target_unit_meters = 1;
        opts.space_conversion = UFBX_SPACE_CONVERSION_ADJUST_TRANSFORMS;
        opts.generate_missing_normals = true;
        opts.geometry_transform_handling = UFBX_GEOMETRY_TRANSFORM_HANDLING_HELPER_NODES;
        opts.geometry_transform_helper_name = { "geo", 3 };
        ufbx_error error = {};
        ufbx_scene* scene = ufbx_load_file(argv[1], &opts, &error);
        if (!scene) throw std::runtime_error(error.description.data);

        json nodes = json::array();
        size_t renderers = 0, triangles = 0;
        // 親は 0 = FBX のルート (呼び出し側が置き換える)。ノード番号は 1 始まり
        std::function<void(const ufbx_node*, size_t, size_t)> visit;
        visit = [&](const ufbx_node* node, size_t parent, size_t childIndex) {
            const size_t id = nodes.size() + 1;
            const auto& t = node->local_transform;
            json entry = {
                { "id", id }, { "parent", parent }, { "childIndex", childIndex },
                { "name", std::string(node->name.data, node->name.length) },
                { "position", { float(t.translation.x), float(t.translation.y), float(t.translation.z) } },
                { "rotation", { float(t.rotation.x), float(t.rotation.y), float(t.rotation.z), float(t.rotation.w) } },
                { "scale", { float(t.scale.x), float(t.scale.y), float(t.scale.z) } },
                { "parts", json::array() },
            };
            if (const auto* mesh = node->mesh) {
                if (mesh->skin_deformers.count) throw std::runtime_error("static stage exporter does not support skins");
                const auto* matNode = node->is_geometry_transform_helper && node->parent ? node->parent : node;
                const auto& mats = matNode->materials.count ? matNode->materials : mesh->materials;
                for (size_t pi = 0; pi < mesh->material_parts.count; ++pi) {
                    const auto& part = mesh->material_parts.data[pi];
                    if (!part.num_triangles) throw std::runtime_error("empty mesh part");
                    const auto* mat = part.index < mats.count ? mats.data[part.index] : nullptr;
                    json p = {
                        { "meshKey", "#mesh" + std::to_string(mesh->element_id) + "#part" + std::to_string(pi) },
                        { "matKey", mat ? "#mat" + std::to_string(mat->element_id) : std::string("#defaultmat") },
                        { "material", mat ? std::string(mat->name.data, mat->name.length) : std::string() },
                        { "triangles", part.num_triangles },
                    };
                    entry["parts"].push_back(p);
                    ++renderers;
                    triangles += part.num_triangles;
                }
            }
            nodes.push_back(entry);
            for (size_t i = 0; i < node->children.count; ++i) visit(node->children.data[i], id, i);
        };
        for (size_t i = 0; i < scene->root_node->children.count; ++i) visit(scene->root_node->children.data[i], 0, i);

        json materials = json::array();
        for (size_t i = 0; i < scene->materials.count; ++i) {
            const ufbx_material* m = scene->materials.data[i];
            json textures = json::array();
            for (size_t ti = 0; ti < m->textures.count; ++ti) {
                const ufbx_texture* tex = m->textures.data[ti].texture;
                textures.push_back({ { "prop", std::string(m->textures.data[ti].material_prop.data, m->textures.data[ti].material_prop.length) },
                                     { "relative", std::string(tex->relative_filename.data, tex->relative_filename.length) } });
            }
            materials.push_back({ { "key", "#mat" + std::to_string(m->element_id) },
                                  { "name", std::string(m->name.data, m->name.length) },
                                  { "metalness", m->pbr.metalness.has_value ? json(m->pbr.metalness.value_real) : json() },
                                  { "roughness", m->pbr.roughness.has_value ? json(m->pbr.roughness.value_real) : json() },
                                  { "opacity", m->pbr.opacity.has_value ? json(m->pbr.opacity.value_real) : json() },
                                  { "textures", textures } });
        }
        json result = { { "source", argv[1] }, { "renderers", renderers }, { "triangles", triangles },
                        { "nodes", nodes }, { "materials", materials } };
        std::ofstream out(argv[2], std::ios::binary);
        out << result.dump(2) << '\n';
        if (!out) throw std::runtime_error("cannot write visual nodes");
        ufbx_free_scene(scene);
        std::cout << "PASS: " << renderers << " FBX renderers; " << triangles << " triangles; "
                  << materials.size() << " materials\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
