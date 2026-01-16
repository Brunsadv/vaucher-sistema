'use client'

import { useState, useEffect } from 'react'
import { Download, X, Smartphone, Share } from 'lucide-react'

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

export default function PWAInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null)
  const [showPrompt, setShowPrompt] = useState(false)
  const [isIOS, setIsIOS] = useState(false)
  const [isStandalone, setIsStandalone] = useState(false)

  useEffect(() => {
    // Verificar se já está instalado
    const standalone = window.matchMedia('(display-mode: standalone)').matches
      || (window.navigator as any).standalone === true
    setIsStandalone(standalone)
    
    if (standalone) return

    // Detectar iOS
    const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream
    setIsIOS(ios)

    // Verificar se foi dispensado recentemente (7 dias)
    const dismissed = localStorage.getItem('pwa-dismissed')
    if (dismissed) {
      const days = (Date.now() - new Date(dismissed).getTime()) / (1000 * 60 * 60 * 24)
      if (days < 7) return
    }

    // Android/Chrome: escutar evento de instalação
    const handler = (e: Event) => {
      e.preventDefault()
      setDeferredPrompt(e as BeforeInstallPromptEvent)
      setTimeout(() => setShowPrompt(true), 2000)
    }
    window.addEventListener('beforeinstallprompt', handler)

    // iOS: mostrar instruções após delay
    if (ios) {
      setTimeout(() => setShowPrompt(true), 3000)
    }

    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  const handleInstall = async () => {
    if (!deferredPrompt) return
    
    deferredPrompt.prompt()
    const { outcome } = await deferredPrompt.userChoice
    
    if (outcome === 'accepted') {
      console.log('App instalado!')
    }
    
    setDeferredPrompt(null)
    setShowPrompt(false)
  }

  const handleDismiss = () => {
    setShowPrompt(false)
    localStorage.setItem('pwa-dismissed', new Date().toISOString())
  }

  if (isStandalone || !showPrompt) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4 animate-slideUp">
      <div className="max-w-md mx-auto bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-red-800 to-red-900 p-4 text-white">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
              <Smartphone className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-lg">Instalar App</h3>
              <p className="text-red-100 text-sm">Acesso rápido pelo celular</p>
            </div>
            <button onClick={handleDismiss} className="p-2 hover:bg-white/10 rounded-lg">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Conteúdo */}
        <div className="p-4">
          {isIOS ? (
            <div className="space-y-3">
              <p className="text-gray-600 text-sm">Para instalar no iPhone:</p>
              <ol className="text-sm text-gray-700 space-y-2">
                <li className="flex items-center gap-2">
                  <span className="bg-red-100 text-red-800 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold">1</span>
                  Toque em <Share className="w-4 h-4 inline mx-1" /> <strong>Compartilhar</strong>
                </li>
                <li className="flex items-center gap-2">
                  <span className="bg-red-100 text-red-800 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold">2</span>
                  <strong>Adicionar à Tela de Início</strong>
                </li>
                <li className="flex items-center gap-2">
                  <span className="bg-red-100 text-red-800 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold">3</span>
                  Toque em <strong>Adicionar</strong>
                </li>
              </ol>
              <button
                onClick={handleDismiss}
                className="w-full py-3 bg-gray-100 text-gray-700 rounded-xl font-medium"
              >
                Entendi
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-gray-600 text-sm">
                Instale o app para acessar seus processos direto do celular.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={handleDismiss}
                  className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium"
                >
                  Agora não
                </button>
                <button
                  onClick={handleInstall}
                  className="flex-1 py-3 bg-red-800 text-white rounded-xl font-medium flex items-center justify-center gap-2"
                >
                  <Download className="w-5 h-5" />
                  Instalar
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        @keyframes slideUp {
          from { transform: translateY(100%); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        .animate-slideUp { animation: slideUp 0.3s ease-out; }
      `}</style>
    </div>
  )
}
