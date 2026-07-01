import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Navbar, Nav, Container, Button } from 'react-bootstrap'
import { useAuth } from '../context/AuthContext'

const NavBar: React.FC = () => {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <Navbar bg="white" expand="lg" className="border-bottom shadow-sm sticky-top">
      <Container fluid>
        <Navbar.Brand as={Link} to="/" className="fw-bold">
          超导文献数据库
        </Navbar.Brand>
        <Navbar.Toggle />
        <Navbar.Collapse>
          <Nav className="me-auto">
            <Nav.Link as={Link} to="/rag" active={location.pathname === '/rag'}>
              AI 助手
            </Nav.Link>
            <Nav.Link as={Link} to="/compound" active={location.pathname.startsWith('/compound')}>
              化合物
            </Nav.Link>
          </Nav>
          <Nav>
            {user ? (
              <>
                <Navbar.Text className="me-3">{user.username}</Navbar.Text>
                <Button variant="outline-secondary" size="sm" onClick={logout}>
                  退出
                </Button>
              </>
            ) : (
              <Nav.Link as={Link} to="/login">
                登录
              </Nav.Link>
            )}
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  )
}

export default NavBar
