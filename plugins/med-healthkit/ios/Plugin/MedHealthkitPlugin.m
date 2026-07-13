#import <Foundation/Foundation.h>
#import <Capacitor/Capacitor.h>

// Registers the Swift plugin with Capacitor so the WebView can call it as
// Capacitor.Plugins.MedHealthkit.<method>().
CAP_PLUGIN(MedHealthkitPlugin, "MedHealthkit",
    CAP_PLUGIN_METHOD(isAvailable, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(requestAuthorization, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(queryClinicalRecords, CAPPluginReturnPromise);
)
