import { useEffect, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { type Student, updateStudent } from "@/api/students"

const LEVELS = ["beginner", "intermediate", "advanced"]

interface Props {
  student: Student | null
  onOpenChange: (student: Student | null) => void
}

export function EditStudentDialog({ student, onOpenChange }: Props) {
  const queryClient = useQueryClient()
  const [firstName, setFirstName] = useState("")
  const [lastName, setLastName] = useState("")
  const [level, setLevel] = useState("")
  const [error, setError] = useState("")

  // Populate fields whenever a new student is passed in
  useEffect(() => {
    if (student) {
      setFirstName(student.first_name)
      setLastName(student.last_name)
      setLevel(student.english_level)
      setError("")
    }
  }, [student])

  const mutation = useMutation({
    mutationFn: (payload: Parameters<typeof updateStudent>[1]) =>
      updateStudent(student!.phone_number, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["students"] })
      onOpenChange(null)
    },
    onError: (err: Error) => setError(err.message),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    mutation.mutate({ first_name: firstName, last_name: lastName, english_level: level })
  }

  return (
    <Dialog open={student !== null} onOpenChange={(open) => !open && onOpenChange(null)}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit Student</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          <div className="space-y-1.5">
            <Label>Phone Number</Label>
            <Input value={student?.phone_number ?? ""} disabled className="font-mono" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="edit-first">First Name</Label>
              <Input
                id="edit-first"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit-last">Last Name</Label>
              <Input
                id="edit-last"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-level">Level</Label>
            <Select value={level} onValueChange={setLevel} required>
              <SelectTrigger id="edit-level">
                <SelectValue placeholder="Select level…" />
              </SelectTrigger>
              <SelectContent>
                {LEVELS.map((l) => (
                  <SelectItem key={l} value={l}>
                    {l.charAt(0).toUpperCase() + l.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(null)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending || !level}>
              {mutation.isPending ? "Saving…" : "Save"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
