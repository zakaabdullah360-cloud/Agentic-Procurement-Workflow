import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const createWorkflow = (request_text) =>
  client.post('/workflows', { request_text }).then((r) => r.data)

export const getWorkflow = (id) =>
  client.get(`/workflows/${id}`).then((r) => r.data)

export const listWorkflows = () =>
  client.get('/workflows').then((r) => r.data)

export const getSteps = (id) =>
  client.get(`/workflows/${id}/steps`).then((r) => r.data)

export const getLogs = (id) =>
  client.get(`/workflows/${id}/logs`).then((r) => r.data)

export const listSuppliers = () =>
  client.get('/suppliers').then((r) => r.data)

export const approve = (approvalId, approver, comment) =>
  client.post(`/approvals/${approvalId}/approve`, { approver, comment }).then((r) => r.data)

export const reject = (approvalId, approver, comment) =>
  client.post(`/approvals/${approvalId}/reject`, { approver, comment }).then((r) => r.data)

export const poDownloadUrl = (poId) => `/api/purchase-orders/${poId}/download`
