/**
 * Larteh Lingo Engine API Client.
 *
 * Facilitates REST interactions with Flask `/api/v1` backend endpoints.
 */

const API_ORIGIN = import.meta.env.VITE_API_ORIGIN || '';
const API_BASE = import.meta.env.VITE_API_URL || `${API_ORIGIN}/api/v1`;

export async function fetchCategories() {
  const response = await fetch(`${API_BASE}/categories`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || 'Failed to fetch taxonomy categories');
  }
  const result = await response.json();
  return result.data || [];
}

export async function createCategory(payload) {
  const response = await fetch(`${API_BASE}/categories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || 'Failed to create category');
  }
  const result = await response.json();
  return result.data;
}

export async function fetchLexicon(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, val);
    }
  });

  const response = await fetch(`${API_BASE}/lexicon?${query.toString()}`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || 'Failed to fetch lexicon entries');
  }
  return await response.json();
}

export async function uploadLexiconEntry(formData) {
  const response = await fetch(`${API_BASE}/lexicon/upload`, {
    method: 'POST',
    body: formData,
    // Note: Do not set Content-Type header manually for FormData; browser sets multipart/form-data boundary automatically
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || `Upload failed with status: ${response.status}`);
  }

  return await response.json();
}
