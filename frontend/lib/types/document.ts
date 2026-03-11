export type Address = {
  street: string | null;
  ward: string | null;
  district: string | null;
  province: string | null;
  country: string;
};

export type PersonalData = {
  full_name: string | null;
  full_name_latin: string | null;
  date_of_birth: string | null;
  gender: "Nam" | "Nữ" | null;
  nationality: string;
  id_number: string | null;
  id_issue_date: string | null;
  id_issue_place: string | null;
  permanent_address: Address | null;
  temporary_address: Address | null;
  source_document_type: string;
  source_image_path: string;
  extraction_confidence: number;
  field_confidences: Record<string, number>;
  extracted_at: string;
};

export type OCRResponse = {
  personal_data: PersonalData;
  raw_text: string;
  processing_time_ms: number;
};
