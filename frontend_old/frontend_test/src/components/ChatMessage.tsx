import React from 'react'
import { Card } from 'react-bootstrap'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
}

const ChatMessage: React.FC<ChatMessageProps> = ({ role, content }) => {
  const isUser = role === 'user'
  return (
    <div className={`d-flex mb-3 ${isUser ? 'justify-content-end' : 'justify-content-start'}`}>
      <Card
        bg={isUser ? 'primary' : 'light'}
        text={isUser ? 'white' : 'dark'}
        className="shadow-sm"
        style={{ maxWidth: '80%', borderRadius: 16 }}
      >
        <Card.Body className="py-2 px-3">
          {isUser ? `🙋 ${content}` : content}
        </Card.Body>
      </Card>
    </div>
  )
}

export default ChatMessage
