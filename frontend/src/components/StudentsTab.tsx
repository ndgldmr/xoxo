import { useState, useMemo } from "react"
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
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { AddStudentDialog } from "./AddStudentDialog"
import { DeleteConfirmDialog } from "./DeleteConfirmDialog"
import { EditStudentDialog } from "./EditStudentDialog"
import { deactivateStudent, listStudents, reactivateStudent, type Student } from "@/api/students"

export function StudentsTab() {
  const [includeInactive, setIncludeInactive] = useState(false)
  const [search, setSearch] = useState("")
  const [levelFilter, setLevelFilter] = useState("all")
  const [addOpen, setAddOpen] = useState(false)
  const [editStudent, setEditStudent] = useState<Student | null>(null)
  const [deletePhone, setDeletePhone] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: students = [], isLoading, isError, error } = useQuery({
    queryKey: ["students", includeInactive],
    queryFn: () => listStudents(includeInactive),
  })

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return students.filter((s) => {
      const matchesSearch =
        !q ||
        s.phone_number.toLowerCase().includes(q) ||
        s.first_name.toLowerCase().includes(q) ||
        s.last_name.toLowerCase().includes(q)
      const matchesLevel = levelFilter === "all" || s.english_level === levelFilter
      return matchesSearch && matchesLevel
    })
  }, [students, search, levelFilter])

  const deactivate = useMutation({
    mutationFn: deactivateStudent,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["students"] }),
  })

  const reactivate = useMutation({
    mutationFn: reactivateStudent,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["students"] }),
  })

  return (
    <div className="space-y-4">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={() => setAddOpen(true)}>+ Add Student</Button>

          <Input
            placeholder="Search by name or phone…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-56"
          />

          <Select value={levelFilter} onValueChange={setLevelFilter}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="All levels" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All levels</SelectItem>
              <SelectItem value="beginner">Beginner</SelectItem>
              <SelectItem value="intermediate">Intermediate</SelectItem>
              <SelectItem value="advanced">Advanced</SelectItem>
            </SelectContent>
          </Select>

          <label className="flex cursor-pointer items-center gap-2 text-sm select-none">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-border"
              checked={includeInactive}
              onChange={(e) => setIncludeInactive(e.target.checked)}
            />
            Show inactive
          </label>

          {(search || levelFilter !== "all") && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setSearch(""); setLevelFilter("all") }}
            >
              Clear filters
            </Button>
          )}
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
                {filtered.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      {students.length === 0 ? "No students found." : "No students match your filters."}
                    </TableCell>
                  </TableRow>
                )}
                {filtered.map((s) => (
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

      <AddStudentDialog open={addOpen} onOpenChange={setAddOpen} />
      <EditStudentDialog student={editStudent} onOpenChange={setEditStudent} />
      <DeleteConfirmDialog phone={deletePhone} onOpenChange={setDeletePhone} />
    </div>
  )
}
