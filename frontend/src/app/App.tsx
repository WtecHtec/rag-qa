import { AppRouter } from "./router";
import type { ChatGateway } from "../features/chat/types/chat";
import type { KnowledgeBaseGateway } from "../features/knowledge-base/types/knowledgeBase";

interface AppProps {
  chatGateway?: ChatGateway;
  knowledgeBaseGateway?: KnowledgeBaseGateway;
}

export function App({ chatGateway, knowledgeBaseGateway }: AppProps) {
  return (
    <AppRouter
      chatGateway={chatGateway}
      knowledgeBaseGateway={knowledgeBaseGateway}
    />
  );
}
