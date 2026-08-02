import axios from 'axios';

const API_URL = "http://127.0.0.1:8085/api";

export interface Transaction {
  id?: number;
  ref_number: string;
  user_id: string;
  amount: number;
  type: string;
  status: string;
  is_anomalous: boolean;
  datetime?: string;
  platform_name?: string;
  method_name?: string;
  platform_url?: string;
  method_type?: string;
}

export interface PlatformBreakdown {
  id: number;
  name: string;
  url: string;
  transaction_count: number;
  deposit_volume: number;
  withdrawal_volume: number;
  anomaly_count: number;
  success_count: number;
  failed_count: number;
  first_transaction: string | null;
  last_transaction: string | null;
  scan_status: string;
}

export interface StatsOverview {
  data_quality: string;
  source: string;
  generated_at: string;
  totals: {
    platforms: number;
    transactions: number;
    deposits: number;
    withdrawals: number;
    successful_transactions: number;
    failed_transactions: number;
    anomalous_transactions: number;
    payment_methods: number;
    reviews: number;
    complaints: number;
    news_articles: number;
    active_scan_jobs: number;
  };
  platforms_breakdown: PlatformBreakdown[];
  payment_methods_by_type: Record<string, number>;
  top_payment_methods: { name: string; type: string; transaction_count: number }[];
  pipeline_mode: string;
  pipeline_status: Record<string, { status: string; mode?: string; reason?: string; records?: number }>;
}

export interface ChatMessage {
  sender: 'user' | 'bot';
  text: string;
  context?: any[];
}

export const apiService = {
  async getStatsOverview(): Promise<StatsOverview> {
    const res = await axios.get(`${API_URL}/stats/overview`);
    return res.data;
  },

  async getTransactions(): Promise<Transaction[]> {
    const res = await axios.get(`${API_URL}/transactions`);
    return res.data;
  },

  async getAnomalies(): Promise<Transaction[]> {
    const res = await axios.get(`${API_URL}/transactions/anomalies`);
    return res.data;
  },

  async getTransactionsByPlatform(platformId: number) {
    const res = await axios.get(`${API_URL}/transactions/by-platform/${platformId}`);
    return res.data;
  },

  async getPlatformDetail(platformId: number) {
    const res = await axios.get(`${API_URL}/platforms/${platformId}/detail`);
    return res.data;
  },

  async getPlatforms() {
    const res = await axios.get(`${API_URL}/platforms`);
    return res.data;
  },

  async getRecentActivity() {
    const res = await axios.get(`${API_URL}/activity/recent`);
    return res.data;
  },

  async getScanJobs() {
    const res = await axios.get(`${API_URL}/scan/jobs`);
    return res.data;
  },

  async startNewScan(url: string) {
    const res = await axios.post(`${API_URL}/scan/new`, { url });
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
  },

  async downloadReportMarkdown() {
    const res = await axios.get(`${API_URL}/agents/report/markdown`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/markdown' }));
    const a = document.createElement('a'); a.href = url;
    a.download = 'sentinelx_audit_report.md';
    document.body.appendChild(a); a.click(); a.remove();
    window.URL.revokeObjectURL(url);
  },

  async downloadReportJson() {
    const res = await axios.get(`${API_URL}/agents/report/json`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/json' }));
    const a = document.createElement('a'); a.href = url;
    a.download = 'sentinelx_audit_report.json';
    document.body.appendChild(a); a.click(); a.remove();
    window.URL.revokeObjectURL(url);
  },

  async queryIntelligentAgent(query: string) {
    const res = await axios.post(`${API_URL}/agents/intelligent-query`, { query });
    return res.data;
  }
};
