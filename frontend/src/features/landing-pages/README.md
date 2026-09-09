# Templates de Landing Page

Estrutura modular para demos comerciais do ProspectOS.

## Estrutura

```text
landing-pages/
├── components/
│   ├── BudgetSimulator.tsx
│   ├── FloatingWhatsApp.tsx
│   ├── HeroSection.tsx
│   ├── ServicesGallery.tsx
│   ├── SocialProofSection.tsx
│   └── TrustBar.tsx
├── templates/
│   └── estetica-premium/
│       └── site.ts
├── LandingPageTemplate.tsx
├── types.ts
└── utils.ts
```

A rota de demonstração atual é:

```text
/demos/estetica-premium
```

## Personalizar para um lead

A apresentação inteira é alimentada pelo arquivo `templates/estetica-premium/site.ts`.
Para criar uma demo individual:

1. Duplique a pasta do template.
2. Altere nome, logo, textos, paleta, fotos, depoimentos, serviços e telefone.
3. Crie uma página fina em `src/pages/demos` que apenas injete o novo objeto em `LandingPageTemplate`.
4. Registre a rota no `App.tsx`.

Exemplo:

```tsx
import { LandingPageTemplate } from "@/features/landing-pages/LandingPageTemplate"
import { clienteSite } from "@/features/landing-pages/templates/cliente/site"

export function ClienteDemoPage() {
  return <LandingPageTemplate site={clienteSite} />
}
```

## Campos de troca rápida

- `brand`: nome e logo.
- `palette`: cores da apresentação sem editar componentes.
- `contact`: WhatsApp, cidade e Instagram.
- `hero`: promessa principal, CTAs e imagem de destaque.
- `trust`: métricas da barra de confiança.
- `services`: cards, modal e valores usados no simulador.
- `testimonials`: depoimentos.
- `faqs`: objeções e dúvidas frequentes.
- `budget`: preço base e textos do simulador.
- `finalCta`: fechamento da página.

## Cuidados para produção

- Substituir fotos externas por assets próprios ou CDN controlada.
- Usar apenas depoimentos autorizados; os atuais são conteúdo demonstrativo.
- Validar telefone no formato internacional, sem símbolos.
- Revisar promessas, preços e restrições regulatórias de cada nicho antes de publicar.
