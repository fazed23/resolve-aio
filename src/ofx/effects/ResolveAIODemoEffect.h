#pragma once

#include "ofxImageEffect.h"
#include "ofxCore.h"

namespace resolve_aio::ofx {

void set_host(OfxHost* host);
OfxPlugin* get_plugin();

}  // namespace resolve_aio::ofx
