import { API_BASE_URL } from "@wdts/api-client";
import {
  EmptyState,
  ErrorState as BaseErrorState,
  LoadingState,
} from "@wdts/ui";

export { EmptyState, LoadingState };

export function ErrorState({ message }: { message: string }) {
  return <BaseErrorState detail={`API base URL: ${API_BASE_URL}`} message={message} />;
}
