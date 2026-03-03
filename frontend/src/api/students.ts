import { apiFetch } from "./client"

export interface Student {
  phone_number: string
  first_name: string
  last_name: string
  english_level: string
  whatsapp_messages: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreateStudentPayload {
  phone_number: string
  first_name: string
  last_name: string
  english_level: string
}

export function listStudents(includeInactive: boolean): Promise<Student[]> {
  return apiFetch(`/students?include_inactive=${includeInactive}`)
}

export function createStudent(payload: CreateStudentPayload): Promise<Student> {
  return apiFetch("/students", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function deactivateStudent(phone: string): Promise<Student> {
  return apiFetch(`/students/${encodeURIComponent(phone)}/deactivate`, { method: "POST" })
}

export function reactivateStudent(phone: string): Promise<Student> {
  return apiFetch(`/students/${encodeURIComponent(phone)}/reactivate`, { method: "POST" })
}

export interface UpdateStudentPayload {
  first_name?: string
  last_name?: string
  english_level?: string
  whatsapp_messages?: boolean
}

export function updateStudent(phone: string, payload: UpdateStudentPayload): Promise<Student> {
  return apiFetch(`/students/${encodeURIComponent(phone)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
}

export function deleteStudent(phone: string): Promise<void> {
  return apiFetch(`/students/${encodeURIComponent(phone)}`, { method: "DELETE" })
}
