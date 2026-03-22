#include "effects/ResolveAIODemoEffect.h"

extern "C" {

OfxExport int OfxGetNumberOfPlugins(void) {
    return 1;
}

OfxExport OfxPlugin* OfxGetPlugin(int nth) {
    if (nth != 0) {
        return nullptr;
    }
    return resolve_aio::ofx::get_plugin();
}

}
