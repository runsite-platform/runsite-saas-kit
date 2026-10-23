import {
  BarChart3,
  Boxes,
  CreditCard,
  KeyRound,
  Palette,
  ShieldCheck,
  Upload,
  Users,
  type LucideIcon,
} from 'lucide-react'

export type KitPartId = 'auth' | 'organizations' | 'billing' | 'dashboard' | 'files' | 'admin' | 'modules' | 'theming'

export interface KitPart {
  id: KitPartId
  icon: LucideIcon
  titleKey: string
  descriptionKey: string
}

export const KIT_PARTS: readonly KitPart[] = [
  { id: 'auth', icon: KeyRound, titleKey: 'landing:features.auth.title', descriptionKey: 'landing:features.auth.description' },
  {
    id: 'organizations',
    icon: Users,
    titleKey: 'landing:features.organizations.title',
    descriptionKey: 'landing:features.organizations.description',
  },
  {
    id: 'billing',
    icon: CreditCard,
    titleKey: 'landing:features.billing.title',
    descriptionKey: 'landing:features.billing.description',
  },
  {
    id: 'dashboard',
    icon: BarChart3,
    titleKey: 'landing:features.dashboard.title',
    descriptionKey: 'landing:features.dashboard.description',
  },
  { id: 'files', icon: Upload, titleKey: 'landing:features.files.title', descriptionKey: 'landing:features.files.description' },
  { id: 'admin', icon: ShieldCheck, titleKey: 'landing:features.admin.title', descriptionKey: 'landing:features.admin.description' },
  {
    id: 'modules',
    icon: Boxes,
    titleKey: 'landing:features.modules.title',
    descriptionKey: 'landing:features.modules.description',
  },
  {
    id: 'theming',
    icon: Palette,
    titleKey: 'landing:features.theming.title',
    descriptionKey: 'landing:features.theming.description',
  },
]
