import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { AddStudentDialog } from "./AddStudentDialog"
import { DeleteConfirmDialog } from "./DeleteConfirmDialog"
import { EditStudentDialog } from "./EditStudentDialog"
import { deactivateStudent, listStudents, reactivateStudent, type Student } from "@/api/students"

interface Props {
  onLogout: () => void
}

export function StudentsTab({ onLogout }: Props) {
  const [includeInactive, setIncludeInactive] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [editStudent, setEditStudent] = useState<Student | null>(null)
  const [deletePhone, setDeletePhone] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: students = [], isLoading, isError, error } = useQuery({
    queryKey: ["students", includeInactive],
    queryFn: () => listStudents(includeInactive),
  })

  const deactivate = useMutation({
    mutationFn: deactivateStudent,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["students"] }),
  })

  const reactivate = useMutation({
    mutationFn: reactivateStudent,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["students"] }),
  })

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-6xl space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">XOXO Admin — Students</h1>
          <Button variant="outline" size="sm" onClick={onLogout}>
            Logout
          </Button>
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-3">
          <Button onClick={() => setAddOpen(true)}>+ Add Student</Button>
          <label className="flex cursor-pointer items-center gap-2 text-sm select-none">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-border"
              checked={includeInactive}
              onChange={(e) => setIncludeInactive(e.target.checked)}
            />
            Show inactive
          </label>
        </div>

        {/* Table */}
        {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
        {isError && (
          <p className="text-sm text-destructive">{(error as Error).message}</p>
        )}
        {!isLoading && !isError && (
          <div className="rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Phone</TableHead>
                  <TableHead>First Name</TableHead>
                  <TableHead>Last Name</TableHead>
                  <TableHead>Level</TableHead>
                  <TableHead>WhatsApp</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {students.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      No students found.
                    </TableCell>
                  </TableRow>
                )}
                {students.map((s) => (
                  <TableRow key={s.phone_number} className={!s.is_active ? "opacity-50" : ""}>
                    <TableCell className="font-mono text-sm">{s.phone_number}</TableCell>
                    <TableCell>{s.first_name}</TableCell>
                    <TableCell>{s.last_name}</TableCell>
                    <TableCell className="capitalize">{s.english_level}</TableCell>
                    <TableCell>{s.whatsapp_messages ? "Yes" : "No"}</TableCell>
                    <TableCell>
                      <Badge variant={s.is_active ? "default" : "secondary"}>
                        {s.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setEditStudent(s)}
                        >
                          Edit
                        </Button>
                        {s.is_active ? (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={deactivate.isPending}
                            onClick={() => deactivate.mutate(s.phone_number)}
                          >
                            Deactivate
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={reactivate.isPending}
                            onClick={() => reactivate.mutate(s.phone_number)}
                          >
                            Reactivate
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => setDeletePhone(s.phone_number)}
                        >
                          Delete
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      <AddStudentDialog open={addOpen} onOpenChange={setAddOpen} />
      <EditStudentDialog student={editStudent} onOpenChange={setEditStudent} />
      <DeleteConfirmDialog phone={deletePhone} onOpenChange={setDeletePhone} />
    </div>
  )
}
