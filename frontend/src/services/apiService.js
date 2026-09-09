const API_BASE = 'http://localhost:8001/api/v1';

export const apiService = {
  async uploadImages(sourceFile, referenceFile) {
    const formData = new FormData();
    formData.append('source', sourceFile);
    formData.append('reference', referenceFile);

    const response = await fetch(`${API_BASE}/upload/`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Failed to upload images');
    }
    return await response.json();
  },

  async triggerRegistration(sessionId) {
    const response = await fetch(`${API_BASE}/registration/${sessionId}`, {
      method: 'POST'
    });

    if (!response.ok) {
      throw new Error('Failed to trigger pipeline');
    }
    return await response.json();
  },

  async fetchResults(sessionId) {
    const response = await fetch(`${API_BASE}/results/${sessionId}/summary`);

    if (!response.ok) {
      throw new Error('Failed to fetch results');
    }
    return await response.json();
  },

  getWebSocketUrl(sessionId) {
    return `ws://localhost:8001/api/v1/registration/ws/progress/${sessionId}`;
  },

  getImageUrl(sessionId, type, idx) {
      return `${API_BASE}/results/${sessionId}/dossier/${idx}/image/${type}`;
  },

  getRawImageUrl(sessionId, type) {
      return `${API_BASE}/results/${sessionId}/image/${type}`;
  },

  getWarpedImageUrl(sessionId) {
      return `${API_BASE}/results/${sessionId}/image/warped`;
  },

  async generateDem(sessionId) {
    const response = await fetch(`${API_BASE}/dem/${sessionId}/generate`, {
      method: 'POST'
    });
    if (!response.ok) {
      throw new Error('Failed to generate DEM');
    }
    return await response.json();
  },

  async fetchDemData(sessionId) {
    const response = await fetch(`${API_BASE}/dem/${sessionId}/data`);
    if (!response.ok) {
      throw new Error('Failed to fetch DEM elevation data');
    }
    return await response.json();
  },

  getDemImageUrl(sessionId, type) {
    return `${API_BASE}/dem/${sessionId}/image/${type}`;
  },

  async loadLocalRealImages(pairType = 'cross_track_stereo') {
    const response = await fetch(`${API_BASE}/upload/load-local-real?pair_type=${pairType}`, {
      method: 'POST'
    });
    if (!response.ok) {
      throw new Error('Failed to load local real images: ' + response.statusText);
    }
    return await response.json();
  }
};