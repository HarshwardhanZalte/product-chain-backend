import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowLeft, ExternalLink, Leaf, Save } from 'lucide-react'
import { useEffect, useMemo } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getApiErrorMessage } from '../api/client'
import { profileApi } from '../api/profiles'
import type { Role } from '../api/types'
import { useAuth } from '../auth/AuthProvider'
import { Button, Card, ErrorState, FieldError, LoadingState, PageHeader, StatusBadge } from '../components/UI'
import { useToast } from '../components/ToastProvider'

const profileFields: Partial<Record<Role, Array<{ name: string; label: string; type?: string }>>> = {
  FARMER: [
    { name: 'farmer_name', label: 'Farmer name' },
    { name: 'phone_number', label: 'Phone number', type: 'tel' },
    { name: 'address', label: 'Farm address' },
    { name: 'village', label: 'Village' },
    { name: 'district', label: 'District' },
    { name: 'state', label: 'State' },
    { name: 'pincode', label: 'Pincode' },
    { name: 'land_area', label: 'Land area' },
    { name: 'land_record_reference', label: 'Land record reference' },
  ],
  COLLECTOR: [
    { name: 'collector_name', label: 'Collector name' },
    { name: 'phone_number', label: 'Phone number', type: 'tel' },
    { name: 'address', label: 'Office address' },
  ],
  LAB: [
    { name: 'laboratory_name', label: 'Laboratory name' },
    { name: 'registration_number', label: 'Registration number' },
    { name: 'address', label: 'Laboratory address' },
    { name: 'contact_number', label: 'Contact number', type: 'tel' },
  ],
  FACTORY: [
    { name: 'factory_name', label: 'Factory name' },
    { name: 'registration_number', label: 'Registration number' },
    { name: 'address', label: 'Factory address' },
    { name: 'contact_number', label: 'Contact number', type: 'tel' },
  ],
}

const profileSchema = z.record(z.string(), z.string())
type ProfileValues = Record<string, string>

export function ProfilePage() {
  const { user } = useAuth()
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const role = user?.role ?? 'ADMIN'
  const fields = useMemo(() => profileFields[role] ?? [], [role])
  const query = useQuery({
    queryKey: ['profile', user?.role],
    queryFn: () => profileApi.get(role),
    enabled: Boolean(user && user.role !== 'ADMIN'),
  })
  const form = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {},
  })
  const mutation = useMutation({
    mutationFn: (values: ProfileValues) => profileApi.update(
      role,
      Object.fromEntries(Object.entries(values).map(([key, value]) => [key, value.trim()])),
    ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['profile'] })
      notify('Profile information saved.')
    },
  })

  useEffect(() => {
    if (!query.data) return
    const values: ProfileValues = {}
    fields.forEach(({ name }) => {
      const value = query.data[name]
      values[name] = value == null ? '' : String(value)
    })
    form.reset(values)
  }, [fields, form, query.data])

  if (user?.role === 'ADMIN') return <AdminEntryPage />
  if (query.isLoading) return <div className="page-content"><LoadingState /></div>
  if (query.error) return <div className="page-content"><ErrorState message={getApiErrorMessage(query.error)} onRetry={() => void query.refetch()} /></div>
  const rawProfileStatus = query.data?.verification_status
  const profileStatus = typeof rawProfileStatus === 'string' ? rawProfileStatus : null

  return (
    <div className="page-content">
      <PageHeader
        eyebrow="Account settings"
        title="Account profile"
        description="Keep your contact and role-profile information current. Verification status is managed by administrators."
      />
      <div className="profile-summary">
        <div className="profile-avatar"><Leaf size={19} /></div>
        <div>
          <strong>{user?.name}</strong>
          <span>{user?.email}</span>
          <span>Email verification: {user?.is_email_verified ? 'Verified' : 'Not verified'}</span>
        </div>
        <StatusBadge value={profileStatus ?? 'Unknown'} />
      </div>
      {mutation.error && <div style={{ marginBottom: 15 }}><ErrorState message={getApiErrorMessage(mutation.error)} /></div>}
      <Card title="Business profile" subtitle="Only fields supported by your role’s backend profile are editable.">
        <div className="card-body">
          <form onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
            <div className="form-grid">
              {fields.map(({ name, label, type }) => (
                <div className="field" key={name}>
                  <label htmlFor={`profile-${name}`}>{label}</label>
                  <input id={`profile-${name}`} type={type ?? 'text'} {...form.register(name)} />
                  <FieldError>{form.formState.errors[name]?.message}</FieldError>
                </div>
              ))}
            </div>
            <div className="form-actions">
              <Button disabled={mutation.isPending} type="submit">{mutation.isPending ? 'Saving…' : 'Save profile'} <Save size={14} /></Button>
            </div>
          </form>
        </div>
      </Card>
    </div>
  )
}

export function AdminEntryPage() {
  const { user } = useAuth()
  const backendBase = import.meta.env.VITE_API_BASE_URL ?? ''
  return (
    <div className="admin-entry">
      <div className="admin-entry-card">
        <span className="brand-mark"><Leaf size={22} /></span>
        <div className="eyebrow">Administrator access</div>
        <h1>Continue to the secure admin panel</h1>
        <p>
          Administrator sign-in uses the Django session panel, separate from participant JWT authentication.
          {user ? ` Signed in to the participant app as ${user.email}.` : ''}
        </p>
        <a className="button button-primary" href={`${backendBase}/panel/login/`}>
          Open administrator login <ExternalLink size={14} />
        </a>
        <Link className="inline-link" to={user ? `/${user.role.toLowerCase()}` : '/login'}>
          <ArrowLeft size={13} /> {user ? 'Return to your workspace' : 'Return to sign in'}
        </Link>
      </div>
    </div>
  )
}
