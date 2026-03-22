#include "ResolveAIODemoEffect.h"

#include <cstring>

#include "ofxProperty.h"

namespace resolve_aio::ofx {
namespace {

constexpr const char* kPluginIdentifier = "io.resolveaio.effects.demo";
constexpr const char* kPluginLabel = "ResolveAIO Demo";
constexpr const char* kPluginGrouping = "ResolveAIO";

OfxHost* g_host = nullptr;
OfxPropertySuiteV1* g_property_suite = nullptr;
OfxImageEffectSuiteV1* g_effect_suite = nullptr;

template <typename T>
T* fetch_suite(const char* name, int version) {
    if (!g_host || !g_host->fetchSuite) {
        return nullptr;
    }
    return reinterpret_cast<T*>(g_host->fetchSuite(g_host->host, name, version));
}

OfxStatus describe(OfxImageEffectHandle effect) {
    if (!g_property_suite || !g_effect_suite) {
        return kOfxStatErrMissingHostFeature;
    }

    OfxPropertySetHandle effect_props = nullptr;
    g_effect_suite->getPropertySet(effect, &effect_props);

    g_property_suite->propSetString(effect_props, kOfxPropLabel, 0, kPluginLabel);
    g_property_suite->propSetString(effect_props, kOfxImageEffectPluginPropGrouping, 0, kPluginGrouping);
    g_property_suite->propSetString(effect_props, kOfxImageEffectPropSupportedContexts, 0, kOfxImageEffectContextFilter);
    g_property_suite->propSetString(effect_props, kOfxImageEffectPropSupportedPixelDepths, 0, kOfxBitDepthByte);
    g_property_suite->propSetString(effect_props, kOfxImageEffectPropSupportedPixelDepths, 1, kOfxBitDepthShort);
    g_property_suite->propSetString(effect_props, kOfxImageEffectPropSupportedPixelDepths, 2, kOfxBitDepthFloat);
    g_property_suite->propSetInt(effect_props, kOfxImageEffectPluginPropSingleInstance, 0, 0);
    g_property_suite->propSetInt(effect_props, kOfxImageEffectPropSupportsTiles, 0, 1);
    return kOfxStatOK;
}

OfxStatus describe_in_context(OfxImageEffectHandle effect) {
    if (!g_property_suite || !g_effect_suite) {
        return kOfxStatErrMissingHostFeature;
    }

    OfxImageClipHandle source_clip = nullptr;
    OfxImageClipHandle output_clip = nullptr;
    g_effect_suite->clipDefine(effect, kOfxImageEffectSimpleSourceClipName, &source_clip);
    g_effect_suite->clipDefine(effect, kOfxImageEffectOutputClipName, &output_clip);

    for (OfxImageClipHandle clip : {source_clip, output_clip}) {
        OfxPropertySetHandle clip_props = nullptr;
        g_effect_suite->clipGetPropertySet(clip, &clip_props);
        g_property_suite->propSetString(clip_props, kOfxImageEffectPropSupportedComponents, 0, kOfxImageComponentRGBA);
        g_property_suite->propSetString(clip_props, kOfxImageEffectPropSupportedComponents, 1, kOfxImageComponentAlpha);
    }

    return kOfxStatOK;
}

OfxStatus create_instance() {
    return kOfxStatOK;
}

OfxStatus destroy_instance() {
    return kOfxStatOK;
}

OfxStatus render() {
    // Placeholder render path: host falls back to default processing.
    // Replace this with CPU/GPU pixel processing when adding a real effect.
    return kOfxStatReplyDefault;
}

OfxStatus main_entry(
    const char* action,
    const void* handle,
    OfxPropertySetHandle /*in_args*/,
    OfxPropertySetHandle /*out_args*/
) {
    if (std::strcmp(action, kOfxActionDescribe) == 0) {
        return describe(reinterpret_cast<OfxImageEffectHandle>(const_cast<void*>(handle)));
    }
    if (std::strcmp(action, kOfxImageEffectActionDescribeInContext) == 0) {
        return describe_in_context(reinterpret_cast<OfxImageEffectHandle>(const_cast<void*>(handle)));
    }
    if (std::strcmp(action, kOfxActionCreateInstance) == 0) {
        return create_instance();
    }
    if (std::strcmp(action, kOfxActionDestroyInstance) == 0) {
        return destroy_instance();
    }
    if (std::strcmp(action, kOfxImageEffectActionRender) == 0) {
        return render();
    }
    return kOfxStatReplyDefault;
}

OfxPlugin kPlugin = {
    kOfxImageEffectPluginApi,
    1,
    kPluginIdentifier,
    OFX_PLUGIN_VERSION_MAJOR,
    OFX_PLUGIN_VERSION_MINOR,
    [](OfxHost* host) {
        set_host(host);
    },
    main_entry,
};

}  // namespace

void set_host(OfxHost* host) {
    g_host = host;
    g_property_suite = fetch_suite<OfxPropertySuiteV1>(kOfxPropertySuite, 1);
    g_effect_suite = fetch_suite<OfxImageEffectSuiteV1>(kOfxImageEffectSuite, 1);
}

OfxPlugin* get_plugin() {
    return &kPlugin;
}

}  // namespace resolve_aio::ofx
