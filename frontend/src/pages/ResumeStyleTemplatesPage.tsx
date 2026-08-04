import { Link } from 'react-router'
import { useTranslation } from 'react-i18next'
import { LayoutTemplate, Palette, FileEdit, FileText, Upload } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export function ResumeStyleTemplatesPage() {
  const { t } = useTranslation()

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-8">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-3xl font-black">{t('myResumes.tabs.styleTemplates')}</h1>
        <Button asChild>
          <Link to="/upload">
            <Upload className="size-4" />
            {t('myResumes.uploadNew')}
          </Link>
        </Button>
      </div>

      <Tabs defaultValue="styleTemplates">
        <TabsList className="flex h-auto flex-wrap gap-1">
          <TabsTrigger value="uploads" asChild className="gap-1">
            <Link to="/resumes">
              <FileText className="size-4" />
              {t('myResumes.tabs.uploads')}
            </Link>
          </TabsTrigger>
          <TabsTrigger value="drafts" asChild className="gap-1">
            <Link to="/resumes">
              <FileEdit className="size-4" />
              {t('myResumes.tabs.drafts')}
            </Link>
          </TabsTrigger>
          <TabsTrigger value="templates" asChild className="gap-1">
            <Link to="/resumes">
              <LayoutTemplate className="size-4" />
              {t('myResumes.tabs.templates')}
            </Link>
          </TabsTrigger>
          <TabsTrigger value="styleTemplates" asChild className="gap-1">
            <Link to="/resumes/style-templates">
              <Palette className="size-4" />
              {t('myResumes.tabs.styleTemplates')}
            </Link>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="styleTemplates">
          <Card>
            <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
              <Palette className="size-10 text-muted-foreground" />
              <p className="text-lg text-muted-foreground">{t('myResumes.noStyleTemplates')}</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
