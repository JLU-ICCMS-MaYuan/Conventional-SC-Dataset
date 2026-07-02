import React from 'react'
import { Button, Card, CardContent } from '@heroui/react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NavBar: React.FC = () => {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <Card className="border-b border-[var(--sc-border)] bg-[rgba(251,253,251,0.9)]">
      <CardContent className="flex min-h-14 items-center justify-between gap-4 px-4 py-2">
        <Link to="/" className="font-bold text-[var(--sc-text)]">SC-Wiki</Link>
        <nav className="toolbar">
          <Link to="/rag"><Button variant={location.pathname === '/rag' ? 'secondary' : 'ghost'} size="sm">超导对话</Button></Link>
          <Link to="/compound"><Button variant={location.pathname.startsWith('/compound') ? 'secondary' : 'ghost'} size="sm">结果页</Button></Link>
        </nav>
        <div className="toolbar">
          {user ? (
            <>
              <span className="text-sm text-[var(--sc-muted)]">{user.username}</span>
              <Button variant="outline" size="sm" onPress={logout}>退出</Button>
            </>
          ) : (
            <Link to="/login"><Button variant="outline" size="sm">登录</Button></Link>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default NavBar
