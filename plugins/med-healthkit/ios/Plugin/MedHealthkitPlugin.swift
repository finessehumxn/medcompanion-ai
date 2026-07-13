import Foundation
import Capacitor
import HealthKit

/**
 * MedHealthkit — reads Apple Health *clinical records* (labs, medications,
 * conditions, allergies, immunizations, procedures, vitals) as FHIR JSON and
 * hands them to the web layer, which maps them into MedCompanion records.
 *
 * Nothing is uploaded here: the FHIR JSON is returned to the in-app WebView,
 * which stores it in on-device localStorage. It only reaches the server if the
 * user later taps an AI feature (and consents), consistent with the app's
 * local-first, AI-optional data policy.
 */
@objc(MedHealthkitPlugin)
public class MedHealthkitPlugin: CAPPlugin {
    private let store = HKHealthStore()

    private func clinicalTypes() -> Set<HKClinicalType> {
        var types = Set<HKClinicalType>()
        let ids: [HKClinicalTypeIdentifier] = [
            .labResultRecord, .medicationRecord, .conditionRecord,
            .allergyRecord, .immunizationRecord, .procedureRecord, .vitalSignRecord
        ]
        for id in ids {
            if let t = HKObjectType.clinicalType(forIdentifier: id) { types.insert(t) }
        }
        return types
    }

    @objc func isAvailable(_ call: CAPPluginCall) {
        call.resolve(["available": HKHealthStore.isHealthDataAvailable()])
    }

    @objc func requestAuthorization(_ call: CAPPluginCall) {
        guard HKHealthStore.isHealthDataAvailable() else {
            call.reject("Health data isn't available on this device"); return
        }
        let types = clinicalTypes()
        store.requestAuthorization(toShare: nil, read: types) { success, error in
            if let error = error { call.reject(error.localizedDescription); return }
            call.resolve(["granted": success])
        }
    }

    @objc func queryClinicalRecords(_ call: CAPPluginCall) {
        guard HKHealthStore.isHealthDataAvailable() else {
            call.reject("Health data isn't available"); return
        }
        let types = Array(clinicalTypes())
        var samples: [String] = []
        let lock = NSLock()
        let group = DispatchGroup()

        for type in types {
            group.enter()
            let query = HKSampleQuery(
                sampleType: type, predicate: nil,
                limit: HKObjectQueryNoLimit, sortDescriptors: nil
            ) { _, results, _ in
                if let records = results as? [HKClinicalRecord] {
                    for record in records {
                        if let data = record.fhirResource?.data,
                           let json = String(data: data, encoding: .utf8) {
                            lock.lock(); samples.append(json); lock.unlock()
                        }
                    }
                }
                group.leave()
            }
            store.execute(query)
        }

        group.notify(queue: .main) {
            call.resolve(["samples": samples])
        }
    }
}
