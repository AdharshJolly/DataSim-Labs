import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface FeedbackLearningCardProps {
  feedbackRating: number;
  feedbackComment: string;
  feedbackBusy: boolean;
  onRatingSelect: (rating: number) => void;
  onCommentChange: (value: string) => void;
  onSubmit: () => void;
}

export function FeedbackLearningCard({
  feedbackRating,
  feedbackComment,
  feedbackBusy,
  onRatingSelect,
  onCommentChange,
  onSubmit,
}: FeedbackLearningCardProps) {
  return (
    <Card className="border-border bg-card/70 p-4">
      <p className="text-sm font-semibold text-foreground">Feedback Learning</p>
      <p className="mt-1 text-xs text-muted-foreground">
        Rate this generation to improve future recommendations.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {[1, 2, 3, 4, 5].map((rating) => (
          <button
            key={`feedback-${rating}`}
            type="button"
            className={`rounded-md border px-3 py-1 text-sm ${
              feedbackRating === rating
                ? "border-primary bg-primary/20 text-primary"
                : "border-border text-muted-foreground hover:border-primary/50"
            }`}
            onClick={() => onRatingSelect(rating)}
          >
            {rating}
          </button>
        ))}
      </div>
      <textarea
        className="mt-3 h-20 w-full"
        placeholder="Optional feedback about quality or realism"
        value={feedbackComment}
        onChange={(e) => onCommentChange(e.target.value)}
      />
      <div className="mt-3">
        <Button
          type="button"
          variant="outline"
          disabled={feedbackBusy || feedbackRating < 1}
          onClick={onSubmit}
        >
          {feedbackBusy ? "Submitting..." : "Submit Feedback"}
        </Button>
      </div>
    </Card>
  );
}
