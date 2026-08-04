import { useState } from "react";

import { ChatComposer } from "./components/ChatComposer";
import { ChatErrorNotice } from "./components/ChatErrorNotice";
import { ChatHeader } from "./components/ChatHeader";
import { CitationInspector } from "./components/CitationInspector";
import { ConversationSidebar } from "./components/ConversationSidebar";
import { DeleteConversationDialog } from "./components/DeleteConversationDialog";
import { ChatTranscript } from "./components/ChatTranscript";
import { useChatWorkspaceContext } from "./hooks/useChatWorkspaceContext";
import { ChatWorkspaceProvider } from "./providers/ChatWorkspaceProvider";
import type { ChatGateway } from "./types/chat";
import type { Conversation } from "./types/chat";
import type { KnowledgeBaseGateway } from "../knowledge-base/types/knowledgeBase";
import "./styles/chat.css";

interface ChatPageProps {
  gateway?: ChatGateway;
  knowledgeBaseGateway?: KnowledgeBaseGateway;
}

export function ChatPage({
  gateway,
  knowledgeBaseGateway,
}: ChatPageProps) {
  return (
    <ChatWorkspaceProvider gateway={gateway} knowledgeBaseGateway={knowledgeBaseGateway}>
      <ChatPageContent />
    </ChatWorkspaceProvider>
  );
}

/** 视图只负责页面编排，流式连接的生命周期由页面级 Provider 管理。 */
export function ChatPageContent() {
  const workspace = useChatWorkspaceContext();
  const [deletingConversation, setDeletingConversation] = useState<Conversation | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const readyKnowledgeBases = workspace.knowledgeBases.filter(
    (item) => item.ready_document_count > 0,
  );
  const readyDocumentCount = readyKnowledgeBases.reduce(
    (total, item) => total + item.ready_document_count,
    0,
  );
  const citationKnowledgeBaseName = workspace.knowledgeBases.find(
    (item) => item.id === workspace.selectedCitation?.knowledge_base_id,
  )?.name;

  const createConversation = () => {
    void workspace.startNewConversation().catch(() => undefined);
  };

  const confirmDeleteConversation = async () => {
    if (!deletingConversation) return;
    setIsDeleting(true);
    try {
      await workspace.deleteConversation(deletingConversation.id);
      setDeletingConversation(null);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <section className={`chat-page${workspace.selectedCitation ? " has-source" : ""}`}>
      <ConversationSidebar
        conversations={workspace.conversations}
        activeId={workspace.activeConversation?.id}
        generatingIds={workspace.generatingConversationIds}
        onNew={() => createConversation()}
        onSelect={workspace.selectConversation}
        onDelete={setDeletingConversation}
      />
      <main className="chat-main">
        <ChatHeader
          title={workspace.activeConversation?.title ?? "新对话"}
          readyKnowledgeBaseCount={readyKnowledgeBases.length}
          readyDocumentCount={readyDocumentCount}
        />
        <ChatErrorNotice error={workspace.error} />
        <ChatTranscript
          conversationId={workspace.activeConversation?.id}
          historyMessages={workspace.historyMessages}
          activeTurn={workspace.activeTurn}
          isLoading={workspace.isLoading}
          isLoadingOlder={workspace.isLoadingOlder}
          hasOlderMessages={workspace.hasOlderMessages}
          onLoadOlder={workspace.loadOlderMessages}
          onCitationSelect={workspace.setSelectedCitation}
          onRegenerate={workspace.regenerate}
          onFeedback={workspace.saveFeedback}
        />
        <div className="chat-composer-dock">
          <ChatComposer
            isGenerating={workspace.isGenerating}
            onSend={workspace.sendMessage}
            onStop={workspace.stopGeneration}
          />
        </div>
      </main>
      <CitationInspector
        citation={workspace.selectedCitation}
        knowledgeBaseName={citationKnowledgeBaseName}
        onClose={() => workspace.setSelectedCitation(null)}
      />
      <DeleteConversationDialog
        conversation={deletingConversation}
        isDeleting={isDeleting}
        isGenerating={deletingConversation
          ? workspace.generatingConversationIds.has(deletingConversation.id)
          : false}
        onClose={() => setDeletingConversation(null)}
        onConfirm={confirmDeleteConversation}
      />
    </section>
  );
}
