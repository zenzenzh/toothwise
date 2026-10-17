// Central role -> capability map for the three-role clinic-staff model.
//
//   dentist       administrator - full access (staff management + audit trail)
//   receptionist  front desk - patient directory only, no clinical data
//   assistant     dental assistant - clinical support (screenings), no notes
//
// The backend is the real security boundary (see backend/app/routers: the
// `require_dentist` / `require_clinical` dependencies). This file only keeps
// the UI in step with it - keep it in sync with the permission matrix in the
// user manual (section 7.3) and the Chapter III/IV requirements tables.

export const ROLES = {
  DENTIST: 'dentist', // administrator
  RECEPTIONIST: 'receptionist',
  ASSISTANT: 'assistant',
};

export const ROLE_LABELS = {
  [ROLES.DENTIST]: 'Dentist (administrator)',
  [ROLES.RECEPTIONIST]: 'Receptionist',
  [ROLES.ASSISTANT]: 'Assistant',
};

const DENTIST = [ROLES.DENTIST];
const CLINICAL = [ROLES.DENTIST, ROLES.ASSISTANT];
const ALL_STAFF = [ROLES.DENTIST, ROLES.RECEPTIONIST, ROLES.ASSISTANT];

export const PERMISSIONS = {
  // Dentist/administrator only.
  manageStaff: DENTIST,
  viewAudit: DENTIST,
  deletePatient: DENTIST,
  writeClinical: DENTIST, // clinical notes, tier confirmation, delete screening
  // Dentist + dental assistant.
  clinical: CLINICAL, // create/view screenings, images, model comparison, PDF
  // Everyone on the clinic side.
  patientDirectory: ALL_STAFF,
};

/** True when the given staff role holds the named capability. */
export function can(role, capability) {
  const allowed = PERMISSIONS[capability];
  return Array.isArray(allowed) && allowed.includes(role);
}

/** True when the account is the dentist (administrator) role. */
export const isDentist = (role) => role === ROLES.DENTIST;
