import { useState } from "react";
import { Calendar, Clock, Sun, CalendarDays } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { RescheduleStepDialog } from "../sequences/RescheduleStepDialog";
import { useRescheduleStep } from "../sequences/hooks/useRescheduleStep";
import type { DailyStepInfo } from "./types";

interface QuickRescheduleMenuProps {
  step: DailyStepInfo;
}

export function QuickRescheduleMenu({ step }: QuickRescheduleMenuProps) {
  const [isCustomDialogOpen, setIsCustomDialogOpen] = useState(false);
  const rescheduleMutation = useRescheduleStep();

  const handleQuickReschedule = (diasAdicionais: number, horasMaisTarde: number = 0) => {
    const dt = new Date();
    if (horasMaisTarde > 0) {
      dt.setHours(dt.getHours() + horasMaisTarde);
    } else {
      dt.setDate(dt.getDate() + diasAdicionais);
      dt.setHours(10, 0, 0, 0); // 10h da manhã por padrão
    }

    rescheduleMutation.mutate({
      stepId: step.id,
      scheduledFor: dt.toISOString(),
    });
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm" className="h-8 text-xs text-muted-foreground gap-1">
            <Clock className="size-3.5" />
            <span>Adiar</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuItem onClick={() => handleQuickReschedule(0, 3)}>
            <Clock className="mr-2 size-4 text-sky-500" />
            <span>Mais tarde hoje (+3h)</span>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => handleQuickReschedule(1)}>
            <Sun className="mr-2 size-4 text-amber-500" />
            <span>Amanhã (10:00)</span>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => handleQuickReschedule(2)}>
            <CalendarDays className="mr-2 size-4 text-emerald-500" />
            <span>Daqui a 2 dias</span>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setIsCustomDialogOpen(true)}>
            <Calendar className="mr-2 size-4" />
            <span>Escolher data...</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <RescheduleStepDialog
        step={step as any}
        open={isCustomDialogOpen}
        onOpenChange={setIsCustomDialogOpen}
      />
    </>
  );
}
