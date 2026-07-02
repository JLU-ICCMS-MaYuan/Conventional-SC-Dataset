import React from 'react'
import { Card, CardContent } from '@heroui/react'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
}

const ChatMessage: React.FC<ChatMessageProps> = ({ role, content }) => {
  const isUser = role === 'user'
  return (
    <div className={`chat-message-row ${isUser ? 'user' : 'assistant'}`}>
      <Card
        className={`chat-bubble ${isUser ? 'user' : ''}`}


      >
        <CardContent className="px-4 py-2 text-sm">
          {content}
        </CardContent>
      </Card>
    </div>
  )
}

export default ChatMessage
