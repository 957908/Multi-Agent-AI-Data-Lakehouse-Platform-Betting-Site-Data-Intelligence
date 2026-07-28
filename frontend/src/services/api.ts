import axios from 'axios';

const API_URL = "http://127.0.0.1:8085/api";

export interface Transaction {
  ref_number: string;
  user_id: string;
  amount: number;
  type: string;
  status: string;
  is_anomalous: boolean;
  datetime?: string;
  platform_name?: string;
  method_name?: string;
}

export interface ChatMessage {
  sender: 'user' | 'bot';
  text: string;
  context?: any[];
}

export const apiService = {
  async getTransactions(): Promise<Transaction[]> {
    const res = await axios.get(`${API_URL}/transactions`);
    return res.data;
  },

  async getAnomalies(): Promise<Transaction[]> {
    const res = await axios.get(`${API_URL}/transactions/anomalies`);
    return res.data;
  },

  async predictAnomaly(amount: number, type: string, status: string) {
    const res = await axios.post(`${API_URL}/predict-anomaly`, { amount, type, status });
    return res.data;
  },

  async queryRAG(query: string) {
    const res = await axios.post(`${API_URL}/query`, { query });
    return res.data;
  },

  async runAgents() {
    const res = await axios.post(`${API_URL}/agents/run`);
    return res.data;
  },

  async getAgentsStatus() {
    const res = await axios.get(`${API_URL}/agents/status`);
    return res.data;
  },

  async approveAgents() {
    const res = await axios.post(`${API_URL}/agents/approve`);
    return res.data;
  },

  async getRAGHealth() {
    const res = await axios.get(`${API_URL}/rag/health`);
    return res.data;
  },

  async getVectorStats() {
    const res = await axios.get(`${API_URL}/vector/stats`);
    return res.data;
  }
};
