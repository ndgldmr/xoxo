import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { deleteStudent } from "@/api/students"

interface Props {
  phone: string | null
  onOpenChange: (phone: string | null) => void
}

export function DeleteConfirmDialog({ phone, onOpenChange }: Props) {
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: deleteStudent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["students"] })
      onOpenChange(null)
    },
  })

  return (
    <Dialog open={phone !== null} onOpenChange={(open) => !open && onOpenChange(null)}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Delete Student</DialogTitle>
          <DialogDescription>
            Permanently delete <span className="font-mono font-medium">{phone}</span>? This action
            cannot be undone.
          </DialogDescription>
        </DialogHeader>
        {mutation.isError && (
          <p className="text-sm text-destructive">{(mutation.error as Error).message}</p>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={() => onOpenChange(null)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={mutation.isPending}
            onClick={() => phone && mutation.mutate(phone)}
          >
            {mutation.isPending ? "Deleting…" : "Delete"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
