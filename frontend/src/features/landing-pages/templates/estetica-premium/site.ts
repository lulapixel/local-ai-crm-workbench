import type { LandingPageData } from "@/features/landing-pages/types"

export const esteticaPremiumSite: LandingPageData = {
  slug: "estetica-premium",
  brand: {
    name: "Auréa Estética",
    eyebrow: "Estética avançada em Curitiba",
  },
  seo: {
    title: "Auréa Estética | Protocolos faciais e corporais personalizados",
    description:
      "Uma experiência premium em estética avançada, com avaliação individual e protocolos personalizados.",
  },
  palette: {
    background: "#0c0a0d",
    surface: "#171218",
    accent: "#e6b8c7",
    accentStrong: "#c77d97",
    text: "#fff8fb",
    muted: "#c8b8bf",
  },
  contact: {
    whatsappNumber: "5541999999999",
    whatsappMessage:
      "Olá! Vi a apresentação da Auréa Estética e gostaria de agendar uma avaliação.",
    city: "Curitiba, PR",
    instagram: "@aureaestetica",
  },
  hero: {
    badge: "Agenda de julho aberta",
    title: "Sua beleza, tratada com",
    highlightedText: "precisão e naturalidade.",
    description:
      "Protocolos faciais e corporais desenhados para você, com acompanhamento próximo, tecnologia e resultados elegantes.",
    primaryCta: "Agendar avaliação",
    secondaryCta: "Explorar tratamentos",
    imageUrl:
      "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?auto=format&fit=crop&w=1400&q=88",
    imageAlt: "Profissional realizando procedimento facial em clínica de estética",
    availabilityLabel: "Próximos horários nesta semana",
  },
  trust: [
    { value: "4,9/5", label: "avaliação média" },
    { value: "+1.200", label: "atendimentos" },
    { value: "7 anos", label: "de experiência" },
    { value: "100%", label: "avaliação individual" },
  ],
  services: [
    {
      id: "harmonizacao",
      title: "Harmonização natural",
      shortDescription: "Equilíbrio facial sem perder sua identidade.",
      description:
        "Planejamento individual para valorizar proporções, suavizar pontos de incômodo e preservar a naturalidade do rosto.",
      imageUrl:
        "https://images.unsplash.com/photo-1616394584738-fc6e612e71b9?auto=format&fit=crop&w=1000&q=85",
      priceFrom: 890,
      duration: "60 a 90 min",
      highlight: "Mais procurado",
    },
    {
      id: "skinbooster",
      title: "Skinbooster",
      shortDescription: "Hidratação profunda e viço uniforme.",
      description:
        "Protocolo para melhorar hidratação, textura e luminosidade da pele com resultado progressivo e delicado.",
      imageUrl:
        "https://images.unsplash.com/photo-1515377905703-c4788e51af15?auto=format&fit=crop&w=1000&q=85",
      priceFrom: 520,
      duration: "45 min",
    },
    {
      id: "bioestimulador",
      title: "Bioestimulador",
      shortDescription: "Firmeza gradual com estímulo de colágeno.",
      description:
        "Tratamento indicado para flacidez e perda de sustentação, com evolução natural ao longo das semanas.",
      imageUrl:
        "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=1000&q=85",
      priceFrom: 1190,
      duration: "60 min",
    },
    {
      id: "corporal",
      title: "Protocolo corporal",
      shortDescription: "Plano combinado para contorno e firmeza.",
      description:
        "Combinação personalizada de tecnologias e acompanhamento para tratar objetivos específicos do corpo.",
      imageUrl:
        "https://images.unsplash.com/photo-1544161515-4ab6ce6db874?auto=format&fit=crop&w=1000&q=85",
      priceFrom: 680,
      duration: "50 a 80 min",
    },
  ],
  testimonials: [
    {
      name: "Marina A.",
      role: "Paciente há 2 anos",
      quote:
        "Foi a primeira vez que senti que alguém realmente ouviu o que eu queria. O resultado ficou leve e muito natural.",
      rating: 5,
    },
    {
      name: "Camila R.",
      role: "Protocolo facial",
      quote:
        "A avaliação foi detalhada, sem pressão. Entendi cada etapa e me senti segura do início ao fim.",
      rating: 5,
    },
    {
      name: "Renata M.",
      role: "Protocolo corporal",
      quote:
        "O espaço é lindo, o atendimento é pontual e o acompanhamento faz diferença. Recomendo muito.",
      rating: 5,
    },
  ],
  faqs: [
    {
      question: "Preciso saber qual procedimento quero?",
      answer:
        "Não. A avaliação existe justamente para entender seu objetivo, histórico e indicar o protocolo mais adequado.",
    },
    {
      question: "Os resultados ficam naturais?",
      answer:
        "Esse é o princípio central da clínica. Cada plano respeita seus traços, proporções e limites individuais.",
    },
    {
      question: "É possível parcelar?",
      answer:
        "Sim. As condições variam de acordo com o protocolo e são apresentadas com transparência durante a avaliação.",
    },
  ],
  budget: {
    title: "Monte uma estimativa inicial",
    description:
      "Selecione seus principais interesses. O valor é apenas uma referência e não substitui a avaliação profissional.",
    basePrice: 180,
    consultationLabel: "Avaliação personalizada",
  },
  finalCta: {
    title: "Seu próximo cuidado pode começar agora.",
    description:
      "Fale diretamente com a equipe e encontre o melhor horário para sua avaliação.",
    buttonLabel: "Conversar pelo WhatsApp",
  },
}
