/**
 * Feature Flags Configuration
 * Set to false as per regulatory simplification directives.
 * Unneeded sections are safely hidden while preserving underlying modules.
 */
export const FEATURES = {
  anomalies: false,
  authorityVerification: false,
  evidenceGraph: false,
  infrastructure: false,
  instituteValidation: false,
  workflow: true,
} as const;

export type FeatureFlag = keyof typeof FEATURES;

