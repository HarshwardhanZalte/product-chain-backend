import { zodResolver } from '@hookform/resolvers/zod'
import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  Beaker,
  Check,
  ChevronRight,
  Factory,
  Leaf,
  LockKeyhole,
  Mail,
  ShieldCheck,
  Sprout,
  Truck,
} from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { z } from 'zod'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { authApi } from '../api/auth'
import { getApiErrorMessage } from '../api/client'
import { profileApi } from '../api/profiles'
import { useAuth } from '../auth/AuthProvider'
import type { Role } from '../api/types'
import { Button, ErrorState, FieldError, LoadingState, StatusBadge } from '../components/UI'

const registrationRoles = [
  { role: 'FARMER', label: 'Farmer', detail: 'Cultivation & harvest', icon: Sprout },
  { role: 'COLLECTOR', label: 'Collector', detail: 'Batch aggregation', icon: Truck },
  { role: 'LAB', label: 'Laboratory', detail: 'Quality testing', icon: Beaker },
  { role: 'FACTORY', label: 'Factory', detail: 'Processing & products', icon: Factory },
] as const

const loginSchema = z.object({
  email: z.string().email('Enter a valid email address.'),
  password: z.string().min(1, 'Enter your password.'),
})
type LoginValues = z.infer<typeof loginSchema>

const registrationSchema = z.object({
  name: z.string().trim().min(2, 'Enter your full name.'),
  email: z.string().email('Enter a valid email address.'),
  phone_number: z.string().max(20, 'Use 20 characters or fewer.'),
  password: z.string().min(8, 'Use at least 8 characters.'),
  confirm_password: z.string().min(8, 'Confirm your password.'),
  role: z.enum(['FARMER', 'COLLECTOR', 'LAB', 'FACTORY']),
}).refine((value) => value.password === value.confirm_password, {
  message: 'Passwords do not match.',
  path: ['confirm_password'],
})
type RegistrationValues = z.infer<typeof registrationSchema>

function AuthFrame({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string
  title: string
  description: string
  children: ReactNode
}) {
  return (
    <div className="auth-page">
      <section className="auth-visual">
        <Link className="auth-brand" to="/">
          <span className="brand-mark"><Leaf size={22} /></span>
          <span>
            <strong>Product Chain</strong>
            <span>Botanical Traceability</span>
          </span>
        </Link>
        <div className="auth-message">
          <div className="eyebrow">Farm-to-bottle traceability</div>
          <h1>Rooted in trust. Traced at every step.</h1>
          <p>
            A connected workspace for Ayurvedic herbs—from harvest and quality
            testing through responsible manufacturing.
          </p>
          <div className="auth-path">
            <span><Sprout size={14} /> Harvest</span>
            <ChevronRight size={13} />
            <span><Beaker size={14} /> Test</span>
            <ChevronRight size={13} />
            <span><Factory size={14} /> Manufacture</span>
          </div>
        </div>
        <div className="auth-bottom">A transparent supply chain, built around real records.</div>
      </section>
      <section className="auth-panel">
        <div className="auth-card">
          <div className="eyebrow">{eyebrow}</div>
          <h2>{title}</h2>
          <p>{description}</p>
          {children}
        </div>
      </section>
    </div>
  )
}

function useErrorMessage() {
  const [message, setMessage] = useState('')
  return { message, setMessage }
}

function nextRoute(status: Awaited<ReturnType<typeof authApi.onboarding>>, role: Role): string {
  if (status.next_step === 'CREATE_PROFILE') return '/onboarding'
  if (status.next_step === 'WAIT_FOR_APPROVAL') return '/pending'
  const destinations: Record<Role, string> = {
    FARMER: '/farmer',
    COLLECTOR: '/collector',
    LAB: '/lab',
    FACTORY: '/factory',
    ADMIN: '/admin',
  }
  return destinations[role]
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const { message, setMessage } = useErrorMessage()
  const [working, setWorking] = useState(false)
  const form = useForm<LoginValues>({ resolver: zodResolver(loginSchema) })

  const submit = async (values: LoginValues) => {
    setWorking(true)
    setMessage('')
    try {
      const user = await login(values.email.trim(), values.password)
      const status = await authApi.onboarding()
      navigate(nextRoute(status, user.role), { replace: true })
    } catch (error) {
      setMessage(getApiErrorMessage(error))
    } finally {
      setWorking(false)
    }
  }

  return (
    <AuthFrame
      eyebrow="Welcome back"
      title="Sign in to your workspace"
      description="Use your registered email and password to continue."
    >
      {message && <div style={{ marginBottom: 15 }}><ErrorState message={message} /></div>}
      <form className="auth-form" onSubmit={form.handleSubmit(submit)}>
        <div className="field">
          <label htmlFor="login-email">Email address</label>
          <input autoComplete="email" id="login-email" placeholder="you@example.com" {...form.register('email')} />
          <FieldError>{form.formState.errors.email?.message}</FieldError>
        </div>
        <div className="field">
          <label htmlFor="login-password">Password</label>
          <input autoComplete="current-password" id="login-password" placeholder="Enter your password" type="password" {...form.register('password')} />
          <FieldError>{form.formState.errors.password?.message}</FieldError>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: -7 }}>
          <Link className="inline-link" to="/forgot-password">Forgot password?</Link>
        </div>
        <Button className="button-full" disabled={working} type="submit">
          {working ? 'Signing in…' : 'Sign in'} <ArrowRight size={15} />
        </Button>
      </form>
      <div className="auth-footer">
        New to Product Chain? <Link to="/register">Create an account</Link>
      </div>
      <div className="auth-footer" style={{ marginTop: 13 }}>
        Administrator? <a href={`${import.meta.env.VITE_API_BASE_URL ?? ''}/panel/login/`}>Open the secure admin panel</a>
      </div>
    </AuthFrame>
  )
}

export function RegisterPage() {
  const navigate = useNavigate()
  const { message, setMessage } = useErrorMessage()
  const [working, setWorking] = useState(false)
  const form = useForm<RegistrationValues>({
    resolver: zodResolver(registrationSchema),
    defaultValues: { role: 'FARMER', phone_number: '' },
  })

  const submit = async ({ confirm_password: _confirm, ...values }: RegistrationValues) => {
    setWorking(true)
    setMessage('')
    try {
      await authApi.register(values)
      navigate(`/verify?email=${encodeURIComponent(values.email.trim().toLowerCase())}`)
    } catch (error) {
      setMessage(getApiErrorMessage(error))
    } finally {
      setWorking(false)
    }
  }

  return (
    <AuthFrame
      eyebrow="Create your account"
      title="Join the traceability network"
      description="Create your account, verify your email, and set up your role profile."
    >
      {message && <div style={{ marginBottom: 14 }}><ErrorState message={message} /></div>}
      <form className="auth-form" onSubmit={form.handleSubmit(submit)}>
        <div className="field">
          <label htmlFor="register-name">Full name</label>
          <input autoComplete="name" id="register-name" placeholder="Your full name" {...form.register('name')} />
          <FieldError>{form.formState.errors.name?.message}</FieldError>
        </div>
        <div className="field">
          <label htmlFor="register-email">Email address</label>
          <input autoComplete="email" id="register-email" placeholder="you@example.com" {...form.register('email')} />
          <FieldError>{form.formState.errors.email?.message}</FieldError>
        </div>
        <div className="field">
          <label htmlFor="register-phone">Phone number <span className="field-hint">(optional)</span></label>
          <input autoComplete="tel" id="register-phone" placeholder="+91 00000 00000" {...form.register('phone_number')} />
          <FieldError>{form.formState.errors.phone_number?.message}</FieldError>
        </div>
        <div className="field">
          <label>Choose your role</label>
          <div className="role-options">
            {registrationRoles.map(({ role, label, detail, icon: Icon }) => (
              <button
                aria-pressed={form.watch('role') === role}
                className={`role-option ${form.watch('role') === role ? 'selected' : ''}`}
                key={role}
                onClick={() => form.setValue('role', role, { shouldValidate: true })}
                type="button"
              >
                <Icon size={18} />
                <span><strong>{label}</strong><small>{detail}</small></span>
              </button>
            ))}
          </div>
        </div>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="register-password">Password</label>
            <input autoComplete="new-password" id="register-password" type="password" {...form.register('password')} />
            <FieldError>{form.formState.errors.password?.message}</FieldError>
          </div>
          <div className="field">
            <label htmlFor="register-confirm">Confirm password</label>
            <input autoComplete="new-password" id="register-confirm" type="password" {...form.register('confirm_password')} />
            <FieldError>{form.formState.errors.confirm_password?.message}</FieldError>
          </div>
        </div>
        <Button className="button-full" disabled={working} type="submit">
          {working ? 'Creating account…' : 'Create account'} <ArrowRight size={15} />
        </Button>
      </form>
      <div className="auth-footer">Already registered? <Link to="/login">Sign in</Link></div>
    </AuthFrame>
  )
}

export function VerifyOtpPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [email, setEmail] = useState(searchParams.get('email') ?? '')
  const [otp, setOtp] = useState('')
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)
  const [working, setWorking] = useState(false)
  const [cooldown, setCooldown] = useState(0)

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = window.setTimeout(() => setCooldown((value) => value - 1), 1000)
    return () => window.clearTimeout(timer)
  }, [cooldown])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setWorking(true)
    setMessage('')
    try {
      const response = await authApi.verifyOtp(email.trim(), otp)
      setIsError(false)
      setMessage(response.detail)
      window.setTimeout(() => navigate('/login'), 900)
    } catch (error) {
      setIsError(true)
      setMessage(getApiErrorMessage(error))
    } finally {
      setWorking(false)
    }
  }

  const resend = async () => {
    setWorking(true)
    setMessage('')
    try {
      const response = await authApi.resendOtp(email.trim())
      setMessage(response.detail)
      setIsError(false)
      setCooldown(60)
    } catch (error) {
      setMessage(getApiErrorMessage(error))
      setIsError(true)
    } finally {
      setWorking(false)
    }
  }

  return (
    <AuthFrame
      eyebrow="Email verification"
      title="Check your inbox"
      description="Enter the six-digit code sent to your email address to verify your account."
    >
      <form className="auth-form" onSubmit={submit}>
        <div className="field">
          <label htmlFor="otp-email">Email address</label>
          <input autoComplete="email" id="otp-email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
        </div>
        <div className="field">
          <label htmlFor="otp-code">6-digit verification code</label>
          <input
            autoComplete="one-time-code"
            id="otp-code"
            inputMode="numeric"
            maxLength={6}
            onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))}
            placeholder="000000"
            required
            value={otp}
          />
        </div>
        {message && (
          <div className={`alert ${isError ? 'alert-error' : 'alert-success'}`}>
            {isError ? <LockKeyhole size={15} /> : <Check size={15} />}{message}
          </div>
        )}
        <Button className="button-full" disabled={working || otp.length !== 6} type="submit">
          {working ? 'Verifying…' : 'Verify email'} <ArrowRight size={15} />
        </Button>
      </form>
      <div className="auth-footer">
        Didn’t receive the code?{' '}
        <button className="inline-link" disabled={working || cooldown > 0} onClick={resend} type="button">
          {cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend code'}
        </button>
      </div>
      <div className="auth-footer"><Link to="/login">Back to sign in</Link></div>
    </AuthFrame>
  )
}

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [otp, setOtp] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [sent, setSent] = useState(false)
  const [working, setWorking] = useState(false)
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)

  const submitEmail = async (event: FormEvent) => {
    event.preventDefault()
    setWorking(true)
    setMessage('')
    try {
      const result = await authApi.forgotPassword(email.trim())
      setMessage(result.detail)
      setIsError(false)
      setSent(true)
    } catch (error) {
      setMessage(getApiErrorMessage(error))
      setIsError(true)
    } finally {
      setWorking(false)
    }
  }

  const submitReset = async (event: FormEvent) => {
    event.preventDefault()
    setWorking(true)
    setMessage('')
    try {
      const result = await authApi.resetPassword({
        email: email.trim(),
        otp,
        new_password: newPassword,
      })
      setMessage(result.detail)
      setIsError(false)
    } catch (error) {
      setMessage(getApiErrorMessage(error))
      setIsError(true)
    } finally {
      setWorking(false)
    }
  }

  return (
    <AuthFrame
      eyebrow="Account recovery"
      title={sent ? 'Set a new password' : 'Reset your password'}
      description={sent ? 'Enter the OTP sent to your email and choose a new password.' : 'We’ll send a reset code to your registered email address.'}
    >
      {message && <div style={{ marginBottom: 14 }} className={`alert ${isError ? 'alert-error' : 'alert-success'}`}>{message}</div>}
      {!sent ? (
        <form className="auth-form" onSubmit={submitEmail}>
          <div className="field">
            <label htmlFor="recovery-email">Email address</label>
            <input autoComplete="email" id="recovery-email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
          </div>
          <Button className="button-full" disabled={working} type="submit">
            {working ? 'Sending…' : 'Send reset code'} <Mail size={15} />
          </Button>
        </form>
      ) : (
        <form className="auth-form" onSubmit={submitReset}>
          <div className="field">
            <label htmlFor="recovery-otp">Verification code</label>
            <input id="recovery-otp" inputMode="numeric" maxLength={6} onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))} required value={otp} />
          </div>
          <div className="field">
            <label htmlFor="recovery-password">New password</label>
            <input autoComplete="new-password" id="recovery-password" minLength={8} onChange={(event) => setNewPassword(event.target.value)} required type="password" value={newPassword} />
          </div>
          <Button className="button-full" disabled={working} type="submit">
            {working ? 'Updating…' : 'Update password'} <ArrowRight size={15} />
          </Button>
        </form>
      )}
      <div className="auth-footer"><Link to="/login">Back to sign in</Link></div>
    </AuthFrame>
  )
}

const profileFields: Record<Exclude<Role, 'ADMIN'>, Array<{
  name: string
  label: string
  required: boolean
}>> = {
  FARMER: [
    { name: 'farmer_name', label: 'Farmer name', required: true },
    { name: 'phone_number', label: 'Phone number', required: true },
    { name: 'address', label: 'Farm address', required: true },
    { name: 'village', label: 'Village', required: true },
    { name: 'district', label: 'District', required: true },
    { name: 'state', label: 'State', required: true },
    { name: 'pincode', label: 'Pincode', required: true },
    { name: 'land_area', label: 'Land area (optional)', required: false },
    { name: 'land_record_reference', label: 'Land record reference (optional)', required: false },
  ],
  COLLECTOR: [
    { name: 'collector_name', label: 'Collector name', required: true },
    { name: 'phone_number', label: 'Phone number', required: true },
    { name: 'address', label: 'Collection office address', required: true },
  ],
  LAB: [
    { name: 'laboratory_name', label: 'Laboratory name', required: true },
    { name: 'registration_number', label: 'Lab registration number', required: true },
    { name: 'address', label: 'Laboratory address', required: true },
    { name: 'contact_number', label: 'Contact number', required: true },
  ],
  FACTORY: [
    { name: 'factory_name', label: 'Factory name', required: true },
    { name: 'registration_number', label: 'Factory registration number', required: true },
    { name: 'address', label: 'Factory address', required: true },
    { name: 'contact_number', label: 'Contact number', required: true },
  ],
}

function profileInitials(role: Role, name: string): Record<string, string> {
  const fields = profileFields[role as Exclude<Role, 'ADMIN'>] ?? []
  const defaults: Record<string, string> = {}
  fields.forEach(({ name: key }) => {
    defaults[key] = key.endsWith('_name') ? name : ''
  })
  return defaults
}

export function OnboardingPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [message, setMessage] = useState('')
  const [working, setWorking] = useState(false)
  const [profileValues, setProfileValues] = useState<Record<string, string>>(
    () => profileInitials(user?.role ?? 'FARMER', user?.name ?? ''),
  )
  const role = user?.role ?? 'FARMER'
  const roleFields = useMemo(
    () => profileFields[role as Exclude<Role, 'ADMIN'>] ?? [],
    [role],
  )

  const submitProfile = async (event: FormEvent) => {
    event.preventDefault()
    setWorking(true)
    setMessage('')
    try {
      const data: Record<string, string | number | null> = {}
      roleFields.forEach(({ name, required }) => {
        const value = profileValues[name]?.trim() ?? ''
        if (required && !value) throw new Error(`${name.replaceAll('_', ' ')} is required.`)
        if (value) data[name] = value
      })
      await profileApi.update(role, data)
      await queryClient.invalidateQueries({ queryKey: ['auth', 'onboarding'] })
      navigate('/pending', { replace: true })
    } catch (error) {
      setMessage(getApiErrorMessage(error))
    } finally {
      setWorking(false)
    }
  }

  const {
    data: onboarding,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['auth', 'onboarding'],
    queryFn: authApi.onboarding,
    retry: false,
  })

  useEffect(() => {
    if (onboarding?.next_step === 'WAIT_FOR_APPROVAL') navigate('/pending', { replace: true })
  }, [onboarding, navigate])

  if (!user) return null
  if (isLoading) return <div className="auth-page"><LoadingState label="Loading your onboarding status…" /></div>
  if (error) return (
    <div className="auth-page">
      <div className="auth-panel" style={{ gridColumn: '1 / -1' }}>
        <div className="auth-card">
          <ErrorState message={getApiErrorMessage(error)} onRetry={() => void refetch()} />
        </div>
      </div>
    </div>
  )
  if (onboarding?.next_step === 'READY') {
    return <Navigate to={`/${role.toLowerCase()}`} replace />
  }

  return (
    <AuthFrame
      eyebrow="Account setup"
      title="Complete your role profile"
      description="Add your role-specific details. Business actions unlock after administrator verification."
    >
      {message && <div style={{ marginBottom: 13 }}><ErrorState message={message} /></div>}
      <form className="auth-form" onSubmit={submitProfile}>
        <div className="form-grid">
          {roleFields.map(({ name, label, required }) => (
            <div className={`field ${name === 'address' ? 'span-2' : ''}`} key={name}>
              <label htmlFor={`profile-${name}`}>{label}</label>
              <input
                autoComplete="off"
                id={`profile-${name}`}
                onChange={(event) => setProfileValues((current) => ({ ...current, [name]: event.target.value }))}
                required={required}
                value={profileValues[name] ?? ''}
              />
            </div>
          ))}
        </div>
        <Button className="button-full" disabled={working} type="submit">
          {working ? 'Saving profile…' : 'Submit for review'} <ArrowRight size={15} />
        </Button>
      </form>
    </AuthFrame>
  )
}

export function PendingApprovalPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const statusQuery = useQuery({
    queryKey: ['auth', 'onboarding'],
    queryFn: authApi.onboarding,
    enabled: Boolean(user),
    retry: false,
  })
  const onboarding = statusQuery.data
  if (onboarding?.next_step === 'READY') {
    return <Navigate to={`/${user?.role.toLowerCase() ?? 'farmer'}`} replace />
  }
  if (onboarding?.next_step === 'CREATE_PROFILE') {
    return <Navigate to="/onboarding" replace />
  }
  const signOut = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <AuthFrame
      eyebrow="Verification in progress"
      title="Your account is under review"
      description="We’ll enable business actions once your role profile has been reviewed."
    >
      {statusQuery.isLoading ? <LoadingState label="Checking your application status…" /> : (
        <>
          {statusQuery.error && <ErrorState message={getApiErrorMessage(statusQuery.error)} onRetry={() => void statusQuery.refetch()} />}
          <div className="card" style={{ padding: 16, marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--forest)', fontSize: 11, fontWeight: 700 }}><BadgeCheck size={15} />Role profile</span>
              <StatusBadge value={onboarding?.role_profile_status ?? 'PENDING'} />
            </div>
          </div>
          <div className="alert"><ShieldCheck size={16} />Business actions become available after your role profile is approved.</div>
          {onboarding?.role_profile_status === 'REJECTED' ? (
            <p className="field-hint" style={{ marginTop: 12 }}>
              An administrator has returned your application for review. Contact your administrator to confirm the required updates; document resubmission is not available in this frontend yet.
            </p>
          ) : null}
          <div className="form-actions" style={{ justifyContent: 'space-between' }}>
            <Button onClick={() => void statusQuery.refetch()} variant="secondary">Refresh status</Button>
            <Button onClick={signOut} variant="quiet"><ArrowLeft size={14} /> Sign out</Button>
          </div>
        </>
      )}
    </AuthFrame>
  )
}
