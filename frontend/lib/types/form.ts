export type FormFieldDefinition = {
  field_name: string;
  field_type: "text" | "date" | "checkbox" | "signature";
  label: string;
  is_required: boolean;
  source: "ocr_extraction" | "user_input" | "derived" | "carry_forward";
};

export type FormFillRequest = {
  form_id: string;
  session_id: string;
  manual_overrides: Record<string, string>;
};

export type FormFillResponse = {
  filled_pdf_path: string;
  filled_fields: Record<string, string>;
  unfilled_required_fields: string[];
};
