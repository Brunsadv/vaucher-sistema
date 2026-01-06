import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Painel Administrativo | Vaucher & Álvares',
  description: 'Painel de gerenciamento de clientes',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  )
}
