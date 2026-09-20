import type { UploadRequest, UploadResponse, ScanRecord, ScanListResponse, StatsResponse } from '../types/contracts';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export class ApiError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch (_err) {
      throw new Error(`HTTP error ${response.status}`, { cause: _err });
    }
    if (errorData && errorData.error) {
      throw new ApiError(errorData.error.code, errorData.error.message);
    }
    throw new Error(`HTTP error ${response.status}`);
  }
  return response.json();
}

export const apiClient = {
  async requestUpload(data: UploadRequest): Promise<UploadResponse> {
    const res = await fetch(`${API_BASE}/upload`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<UploadResponse>(res);
  },

  async uploadFileToS3(uploadUrl: string, file: File): Promise<void> {
    const res = await fetch(uploadUrl, {
      method: 'PUT',
      headers: { 'Content-Type': file.type },
      body: file,
    });
    if (!res.ok) {
      throw new Error(`Failed to upload file to S3: ${res.statusText}`);
    }
  },

  async getScan(scanId: string): Promise<ScanRecord> {
    const res = await fetch(`${API_BASE}/scans/${scanId}`);
    return handleResponse<ScanRecord>(res);
  },

  async listScans(params?: {
    query?: string;
    rule_id?: string;
    status?: string;
    limit?: number;
    last_key?: string;
  }): Promise<ScanListResponse> {
    const url = new URL(`${API_BASE}/scans`);
    if (params) {
      if (params.query) url.searchParams.append('query', params.query);
      if (params.rule_id) url.searchParams.append('rule_id', params.rule_id);
      if (params.status) url.searchParams.append('status', params.status);
      if (params.limit) url.searchParams.append('limit', params.limit.toString());
      if (params.last_key) url.searchParams.append('last_key', params.last_key);
    }
    const res = await fetch(url.toString());
    return handleResponse<ScanListResponse>(res);
  },

  async getStats(): Promise<StatsResponse> {
    const res = await fetch(`${API_BASE}/stats`);
    return handleResponse<StatsResponse>(res);
  },

};

const OUTPUTS_BASE = import.meta.env.VITE_OUTPUTS_PUBLIC_BASE_URL || '';

export function resolveArtifactUrl(relativePath: string | null | undefined): string | null {
  if (!relativePath) return null;
  if (relativePath.startsWith('http://') || relativePath.startsWith('https://')) {
    return relativePath;
  }
  const base = OUTPUTS_BASE.replace(/\/$/, '');
  const path = relativePath.replace(/^\//, '');
  return `${base}/${path}`;
}
