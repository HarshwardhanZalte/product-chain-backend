export type Role = 'FARMER' | 'COLLECTOR' | 'LAB' | 'FACTORY' | 'ADMIN'

export interface User {
  user_id: string
  email: string
  name: string
  phone_number: string
  role: Role
  is_active: boolean
  is_email_verified: boolean
  date_joined: string
}

export interface Tokens {
  access: string
  refresh: string
}

export interface LoginResponse {
  user: User
  tokens: Tokens
}

export interface ApiPage<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface Participant {
  id: number
  user_id: string
  name: string
  role: Exclude<Role, 'FARMER' | 'ADMIN'>
  profile_id: string
  profile_name: string
  profile_registration_number: string | null
}

export interface OnboardingStatus {
  role: Role
  email_verified: boolean
  role_profile: Record<string, unknown> | null
  role_profile_status: string | null
  business_identity_approved: boolean
  next_step: 'VERIFY_EMAIL' | 'CREATE_PROFILE' | 'WAIT_FOR_APPROVAL' | 'READY'
}

export interface HerbBatch {
  id: number
  batch_id: string
  herb_name: string
  botanical_name: string
  plant_part: string
  cultivar: string
  quality_grade: string
  description: string
  packaging_details: string
  drying_notes: string
  gacp_attested: boolean
  quantity: string
  available_quantity: string
  unit: string
  source_type: 'CULTIVATED' | 'WILD_COLLECTED'
  collection_date: string
  collection_time: string
  latitude: string | null
  longitude: string | null
  collection_address: string
  village: string
  district: string
  state: string
  status: string
  remarks: string
  created_at: string
  farmer: number
  current_owner: number
}

export interface FieldEvidence {
  evidence_id: string
  kind: 'PHOTO' | 'DOCUMENT'
  file: string
  label: string
  captured_at: string | null
  latitude: string | null
  longitude: string | null
  created_at: string
}

export interface TransferEvent {
  id: number
  event_id: string
  batch_identifier: string
  herb_name: string
  botanical_name: string
  unit: string
  from_party_name: string
  to_party_name: string
  quantity: string
  transfer_date: string
  transfer_location: string
  remarks: string
  status: string
  created_at: string
  batch: number
  from_party: number
  to_party: number
}

export interface LabMeasurement {
  measurement_id?: string
  analyte: string
  method: string
  result_value: string
  numeric_value: string | null
  unit: string
  threshold: string
  verdict: 'PASS' | 'FAIL' | 'INCONCLUSIVE'
}

export interface LabTest {
  id: number
  test_id: string
  test_date: string
  test_type: string
  test_parameters: Record<string, unknown>
  test_result: string
  result_summary: string
  remarks: string
  certificate_available: boolean
  certificate_hash: string | null
  measurements: LabMeasurement[]
  status: string
  created_at: string
  batch: number
  laboratory: number
  submitted_by: number
  reviewed_by: number | null
  batch_id?: string
  herb_name?: string
  botanical_name?: string
  laboratory_name?: string
}

export interface ManufacturingInput {
  batch_id: string
  herb_name: string
  botanical_name: string
  quantity_used: string
  unit: string
  available_quantity: string
}

export interface ManufacturingRecord {
  id: number
  manufacturing_id: string
  product_name: string
  process_date: string
  process_description: string
  facility_line: string
  shift: string
  standard_operating_procedure: string
  solvent_method: string
  target_yield_ratio: string
  process_parameters: Record<string, unknown>
  quality_control_lead: string
  input_quantity: string
  output_quantity: string
  unit: string
  status: string
  remarks: string
  input_batches: ManufacturingInput[]
  created_at: string
  factory: number
  created_by: number
}

export interface ProductSourceBatch {
  batch_id: string
  herb_name: string
  botanical_name: string
  village: string
  district: string
  state: string
  harvest_date: string
}

export interface Product {
  id: number
  product_id: string
  product_name: string
  description: string
  product_type: string
  manufacture_date: string
  expiry_date: string | null
  batch_number: string
  total_quantity: string
  unit: string
  qr_reference: string
  status: string
  product_image: string | null
  qr_code_image: string | null
  source_batches: ProductSourceBatch[]
  manufacturing: ManufacturingRecord
  manufacturer: number
  manufacturing_record: string
  created_at: string
}

export interface ProductVerification {
  verification_status: 'VERIFIED' | 'INCOMPLETE' | 'REJECTED' | string
  product: {
    product_id: string
    product_name: string
    product_type: string
    manufacture_date: string
    status: string
    manufacturer_name: string
    batch_number: string
    product_image_url: string | null
    qr_code_url: string | null
  }
  manufacturing: {
    process_date: string
    process_description: string
    output_quantity: string
    unit: string
  }
  input_herb_batches: Array<{
    batch_id: string
    herb_name: string
    botanical_name: string
    quantity_used: string
    unit: string
    origin: {
      village: string
      district: string
      state: string
      collection_date: string
    }
    laboratory_test_status: string | null
    certificate_available: boolean
    laboratory_name: string | null
    lab_measurements: LabMeasurement[]
    transfer_history: Array<{
      event_id: string
      status: string
      transfer_date: string
      transfer_location: string
    }>
  }>
}

export interface DashboardCounts {
  total_batches?: number
  registered?: number
  approved?: number
  rejected?: number
  pending_transfers?: number
  accepted_transfers?: number
  pending?: number
  under_testing?: number
  approved_tests?: number
  rejected_tests?: number
  manufacturing_records?: number
  completed?: number
  in_progress?: number
}

export interface ApiDetail {
  detail: string
}
