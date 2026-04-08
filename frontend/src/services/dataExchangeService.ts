import { validateImportFile } from "@/utils/security";
import api from "./api";

/** Allowed Content-Types for blob responses from data exchange endpoints */
const ALLOWED_BLOB_TYPES = new Set([
  "text/csv",
  "application/json",
  "application/pdf",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/octet-stream",
]);

/** Validates that a blob response has an expected Content-Type */
function validateBlobResponse(blob: Blob): Blob {
  if (blob.type && !ALLOWED_BLOB_TYPES.has(blob.type)) {
    throw new Error("data.unexpectedResponseType");
  }
  return blob;
}

// Data Exchange Types
export interface EntityField {
  name: string;
  display_name: string;
  field_type: string;
  required: boolean;
  exportable: boolean;
  importable: boolean;
}

export interface Entity {
  name: string;
  display_name: string;
  exportable: boolean;
  importable: boolean;
  fields: EntityField[];
}

export interface ExportPreview {
  rows: Record<string, unknown>[];
  total_count: number;
}

export interface ImportResult {
  total_rows: number;
  inserted: number;
  updated: number;
  skipped: number;
  error_count: number;
  errors: { row: number; field: string; message: string }[];
  warnings: { row: number; field: string; message: string }[];
  dry_run: boolean;
  duration_ms: number;
  success: boolean;
}

export interface ReportFilter {
  field: string;
  operator: string;
  value: string | number | boolean | null;
}

export interface ReportRequest {
  title?: string;
  filters?: ReportFilter[];
  columns?: string[];
  group_by?: string[];
  sort_by?: string;
  format?: "pdf" | "excel" | "csv";
  include_summary?: boolean;
  date_range_field?: string;
  date_from?: string;
  date_to?: string;
}

export const dataExchangeService = {
  listEntities: async (): Promise<Entity[]> => {
    const response = await api.get<Entity[]>("/data/entities");
    return response.data;
  },

  getEntity: async (entity: string): Promise<Entity> => {
    const response = await api.get<Entity>(
      `/data/entities/${encodeURIComponent(entity)}`,
    );
    return response.data;
  },

  previewExport: async (entity: string, limit = 10): Promise<ExportPreview> => {
    // Clamp limit to prevent excessive server-side serialization (DoS)
    const safeLimit = Math.min(Math.max(1, Math.floor(limit)), 100);
    const response = await api.get<ExportPreview>(
      `/data/export/${encodeURIComponent(entity)}/preview`,
      {
        params: { limit: safeLimit },
      },
    );
    return response.data;
  },

  exportData: async (
    entity: string,
    format: "csv" | "excel" | "json" = "csv",
    columns?: string[],
  ): Promise<Blob> => {
    const response = await api.get(
      `/data/export/${encodeURIComponent(entity)}`,
      {
        params: {
          format,
          columns: columns?.join(","),
        },
        responseType: "blob",
      },
    );
    return validateBlobResponse(response.data);
  },

  downloadTemplate: async (
    entity: string,
    format: "csv" | "excel" = "csv",
  ): Promise<Blob> => {
    const response = await api.get(
      `/data/import/${encodeURIComponent(entity)}/template`,
      {
        params: { format },
        responseType: "blob",
      },
    );
    return validateBlobResponse(response.data);
  },

  validateImport: async (entity: string, file: File): Promise<ImportResult> => {
    const validation = validateImportFile(file);
    if (!validation.valid) {
      throw new Error(validation.error || "common.invalidFile");
    }
    const formData = new FormData();
    formData.append("file", file);

    const response = await api.post<ImportResult>(
      `/data/import/${encodeURIComponent(entity)}?dry_run=true`,
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
      },
    );
    return response.data;
  },

  importData: async (
    entity: string,
    file: File,
    mode: "insert" | "update" | "upsert" = "upsert",
  ): Promise<ImportResult> => {
    const validation = validateImportFile(file);
    if (!validation.valid) {
      throw new Error(validation.error || "common.invalidFile");
    }
    const formData = new FormData();
    formData.append("file", file);

    const response = await api.post<ImportResult>(
      `/data/import/${encodeURIComponent(entity)}?mode=${encodeURIComponent(mode)}&dry_run=false`,
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
      },
    );
    return response.data;
  },

  generateReport: async (
    entity: string,
    options: ReportRequest = {},
  ): Promise<Blob> => {
    const response = await api.post(
      `/data/reports/${encodeURIComponent(entity)}`,
      options,
      {
        responseType: "blob",
      },
    );
    return validateBlobResponse(response.data);
  },

  getReportSummary: async (
    entity: string,
    filters?: ReportFilter[],
  ): Promise<{
    total_records: number;
    grouped_counts: Record<string, number>;
  }> => {
    const response = await api.post(
      `/data/reports/${encodeURIComponent(entity)}/summary`,
      { filters },
    );
    return response.data;
  },
};
