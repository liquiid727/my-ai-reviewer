import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router'
import { getResumeDetail } from '@/api/resume'
import type {
  ResumeDetailData,
  Evidence,
  Education,
  WorkExperience,
  ProjectExperience,
  Skill,
  Certificate,
} from '@/types/resume'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import {
  Mail,
  Phone,
  MapPin,
  ExternalLink,
  GraduationCap,
  Briefcase,
  FolderKanban,
  Wrench,
  Award,
  ArrowRight,
  Loader2,
} from 'lucide-react'

function ConfidenceBadge({ confidence }: { confidence?: number }) {
  if (confidence == null) return null
  const pct = Math.round(confidence * 100)
  if (confidence >= 0.8) {
    return (
      <Badge className="bg-green-400 text-green-900 border-green-700">
        {pct}%
      </Badge>
    )
  }
  if (confidence >= 0.5) {
    return (
      <Badge className="bg-yellow-300 text-yellow-900 border-yellow-700">
        {pct}%
      </Badge>
    )
  }
  return (
    <Badge className="bg-red-400 text-red-900 border-red-700">
      {pct}%
    </Badge>
  )
}

function EvidenceSection({ evidence }: { evidence?: Evidence[] }) {
  if (!evidence || evidence.length === 0) return null
  return (
    <Accordion type="single" collapsible className="mt-3">
      <AccordionItem value="evidence">
        <AccordionTrigger className="text-sm py-2 px-3">
          Source Evidence ({evidence.length})
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-3">
            {evidence.map((ev, i) => (
              <div key={i} className="flex items-start gap-2">
                <div className="flex-1">
                  <p className="text-sm italic text-muted-foreground">
                    &ldquo;{ev.source_text}&rdquo;
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    {ev.page != null && (
                      <span className="text-xs text-muted-foreground">
                        Page {ev.page}
                      </span>
                    )}
                    <ConfidenceBadge confidence={ev.confidence} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}

function DateRange({ start, end }: { start?: string; end?: string }) {
  if (!start && !end) return null
  return (
    <span className="text-sm text-muted-foreground">
      {start ?? '?'} &mdash; {end ?? 'Present'}
    </span>
  )
}

function EducationCard({ edu }: { edu: Education }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <GraduationCap className="size-5" />
          {edu.school}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-1">
          {edu.degree && (
            <p className="text-sm font-medium">{edu.degree}{edu.major ? ` in ${edu.major}` : ''}</p>
          )}
          <DateRange start={edu.start_date} end={edu.end_date} />
          {edu.gpa && (
            <p className="text-sm text-muted-foreground">GPA: {edu.gpa}</p>
          )}
        </div>
        <EvidenceSection evidence={edu.evidence} />
      </CardContent>
    </Card>
  )
}

function WorkExperienceCard({ exp }: { exp: WorkExperience }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Briefcase className="size-5" />
          {exp.company}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {exp.title && <p className="font-medium">{exp.title}</p>}
          <DateRange start={exp.start_date} end={exp.end_date} />
          {exp.description && (
            <p className="text-sm text-muted-foreground">{exp.description}</p>
          )}
          {exp.achievements && exp.achievements.length > 0 && (
            <ul className="list-disc list-inside space-y-1 text-sm">
              {exp.achievements.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          )}
        </div>
        <EvidenceSection evidence={exp.evidence} />
      </CardContent>
    </Card>
  )
}

function ProjectExperienceCard({ proj }: { proj: ProjectExperience }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FolderKanban className="size-5" />
          {proj.name}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {proj.role && (
            <p className="text-sm font-medium">Role: {proj.role}</p>
          )}
          {proj.tech_stack && proj.tech_stack.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {proj.tech_stack.map((tech, i) => (
                <Badge key={i} variant="neutral" className="text-xs">
                  {tech}
                </Badge>
              ))}
            </div>
          )}
          {proj.description && (
            <p className="text-sm text-muted-foreground">{proj.description}</p>
          )}
          {proj.highlights && proj.highlights.length > 0 && (
            <ul className="list-disc list-inside space-y-1 text-sm">
              {proj.highlights.map((h, i) => (
                <li key={i}>{h}</li>
              ))}
            </ul>
          )}
        </div>
        <EvidenceSection evidence={proj.evidence} />
      </CardContent>
    </Card>
  )
}

function SkillCard({ skill }: { skill: Skill }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Wrench className="size-4" />
          {skill.name}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          {skill.level && (
            <Badge variant="neutral">{skill.level}</Badge>
          )}
          {skill.category && (
            <Badge>{skill.category}</Badge>
          )}
        </div>
        <EvidenceSection evidence={skill.evidence} />
      </CardContent>
    </Card>
  )
}

function CertificateCard({ cert }: { cert: Certificate }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Award className="size-4" />
          {cert.name}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-1 text-sm">
          {cert.issuer && <p>Issuer: {cert.issuer}</p>}
          {cert.date && (
            <p className="text-muted-foreground">{cert.date}</p>
          )}
        </div>
        <EvidenceSection evidence={cert.evidence} />
      </CardContent>
    </Card>
  )
}

function ProfileSkeleton() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <Skeleton className="h-8 w-48" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <Skeleton className="h-4 w-64" />
            <Skeleton className="h-4 w-52" />
            <Skeleton className="h-4 w-40" />
            <div className="flex gap-2 mt-4">
              <Skeleton className="h-6 w-20" />
              <Skeleton className="h-6 w-24" />
              <Skeleton className="h-6 w-16" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Skeleton className="h-12 w-full" />
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    </div>
  )
}

export function ResumePage() {
  const { id } = useParams()
  const [resume, setResume] = useState<ResumeDetailData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    setError(null)
    getResumeDetail(id)
      .then((res) => {
        setResume(res.data)
      })
      .catch((err: Error) => {
        setError(err.message ?? 'Failed to load resume')
      })
      .finally(() => {
        setLoading(false)
      })
  }, [id])

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <ProfileSkeleton />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-red-600 font-bold">Error: {error}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!resume) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <Card>
          <CardContent className="pt-6">
            <p>Resume not found.</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const isProcessing = resume.status !== 'evaluated' && resume.status !== 'classified'

  if (isProcessing || !resume.parsed_result) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <Loader2 className="size-10 animate-spin text-main" />
            <p className="text-lg font-heading">Resume is being processed...</p>
            <p className="text-sm text-muted-foreground">
              Current status: <Badge variant="neutral">{resume.status}</Badge>
            </p>
            <p className="text-sm text-muted-foreground">
              Please check back shortly. The parsing and evaluation may take a moment.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const profile = resume.parsed_result.profile
  const classification = resume.parsed_result.classification

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      {/* Profile Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">
            {profile?.name ?? 'Unknown Candidate'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {profile?.email && (
              <div className="flex items-center gap-2 text-sm">
                <Mail className="size-4 shrink-0" />
                <span>{profile.email}</span>
              </div>
            )}
            {profile?.phone && (
              <div className="flex items-center gap-2 text-sm">
                <Phone className="size-4 shrink-0" />
                <span>{profile.phone}</span>
              </div>
            )}
            {profile?.location && (
              <div className="flex items-center gap-2 text-sm">
                <MapPin className="size-4 shrink-0" />
                <span>{profile.location}</span>
              </div>
            )}
          </div>

          {/* Links */}
          {profile?.links && profile.links.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-4">
              {profile.links.map((link, i) => (
                <a
                  key={i}
                  href={link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm underline hover:opacity-70"
                >
                  <ExternalLink className="size-3" />
                  {link}
                </a>
              ))}
            </div>
          )}

          {/* Ability Tags */}
          {profile?.ability_tags && profile.ability_tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-4">
              {profile.ability_tags.map((tag, i) => (
                <Badge key={i}>{tag}</Badge>
              ))}
            </div>
          )}

          {/* Classification Info */}
          {classification && (
            <div className="mt-4 space-y-2">
              {classification.experience_level && (
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Experience Level:</span>
                  <Badge variant="neutral">{classification.experience_level}</Badge>
                </div>
              )}
              {classification.tech_direction_tags && classification.tech_direction_tags.length > 0 && (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium">Tech Direction:</span>
                  {classification.tech_direction_tags.map((tag, i) => (
                    <Badge key={i} variant="neutral">{tag}</Badge>
                  ))}
                </div>
              )}
              {classification.industry_tags && classification.industry_tags.length > 0 && (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium">Industry:</span>
                  {classification.industry_tags.map((tag, i) => (
                    <Badge key={i} variant="neutral">{tag}</Badge>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="education">
        <TabsList className="flex flex-wrap h-auto gap-1">
          <TabsTrigger value="education" className="gap-1">
            <GraduationCap className="size-4" />
            Education
          </TabsTrigger>
          <TabsTrigger value="work" className="gap-1">
            <Briefcase className="size-4" />
            Work Experience
          </TabsTrigger>
          <TabsTrigger value="projects" className="gap-1">
            <FolderKanban className="size-4" />
            Projects
          </TabsTrigger>
          <TabsTrigger value="skills" className="gap-1">
            <Wrench className="size-4" />
            Skills
          </TabsTrigger>
          <TabsTrigger value="certificates" className="gap-1">
            <Award className="size-4" />
            Certificates
          </TabsTrigger>
        </TabsList>

        <TabsContent value="education">
          <div className="space-y-4">
            {profile?.educations && profile.educations.length > 0 ? (
              profile.educations.map((edu, i) => (
                <EducationCard key={i} edu={edu} />
              ))
            ) : (
              <p className="text-sm text-muted-foreground py-4">No education data available.</p>
            )}
          </div>
        </TabsContent>

        <TabsContent value="work">
          <div className="space-y-4">
            {profile?.work_experiences && profile.work_experiences.length > 0 ? (
              profile.work_experiences.map((exp, i) => (
                <WorkExperienceCard key={i} exp={exp} />
              ))
            ) : (
              <p className="text-sm text-muted-foreground py-4">No work experience data available.</p>
            )}
          </div>
        </TabsContent>

        <TabsContent value="projects">
          <div className="space-y-4">
            {profile?.project_experiences && profile.project_experiences.length > 0 ? (
              profile.project_experiences.map((proj, i) => (
                <ProjectExperienceCard key={i} proj={proj} />
              ))
            ) : (
              <p className="text-sm text-muted-foreground py-4">No project data available.</p>
            )}
          </div>
        </TabsContent>

        <TabsContent value="skills">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {profile?.skills && profile.skills.length > 0 ? (
              profile.skills.map((skill, i) => (
                <SkillCard key={i} skill={skill} />
              ))
            ) : (
              <p className="text-sm text-muted-foreground py-4">No skills data available.</p>
            )}
          </div>
        </TabsContent>

        <TabsContent value="certificates">
          <div className="space-y-4">
            {profile?.certificates && profile.certificates.length > 0 ? (
              profile.certificates.map((cert, i) => (
                <CertificateCard key={i} cert={cert} />
              ))
            ) : (
              <p className="text-sm text-muted-foreground py-4">No certificates data available.</p>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Bottom navigation */}
      <div className="flex justify-center pt-4">
        <Button asChild size="lg">
          <Link to={`/resume/${id}/evaluation`}>
            View AI Evaluation Report
            <ArrowRight className="size-4" />
          </Link>
        </Button>
      </div>
    </div>
  )
}
