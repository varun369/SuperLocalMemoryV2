import React, { useState } from 'react';
import { VideoModal } from '../ui/VideoModal';
import { Play } from 'lucide-react';
import { FadeIn } from '../ui/Motion';

const VIDEOS = [
    {
        id: 'dashboard',
        title: 'Dashboard Tour',
        description: 'A complete overview of the memory management interface.',
        src: '/assets/videos/dashboard-tour.mp4',
        type: 'video'
    },
    {
        id: 'installation',
        title: 'Installation',
        description: 'Zero to running in under 30 seconds.',
        src: '/assets/videos/installation-walkthrough.mp4',
        type: 'video'
    },
    {
        id: 'quickstart',
        title: 'Quick Start',
        description: 'Adding your first memory and querying it.',
        src: '/assets/videos/quick-start.mp4',
        type: 'video'
    },
    {
        id: 'graph',
        title: 'Graph Interaction',
        description: 'Visualizing knowledge connections in real-time.',
        src: '/assets/gifs/graph-interaction.gif',
        type: 'image' // Treating GIF as image, but could technically be video if converted
    }
];

export const DemoGallery: React.FC = () => {
    const [selectedVideo, setSelectedVideo] = useState<{ src: string, title: string } | null>(null);

    return (
        <>
            <div className="grid md:grid-cols-2 gap-8">
                {VIDEOS.map((video, index) => (
                    <FadeIn key={video.id} delay={0.1 * index}>
                        <div className="group cursor-pointer" onClick={() => video.type === 'video' && setSelectedVideo({ src: video.src, title: video.title })}>
                            <h3 className="text-xl font-bold text-white mb-2 group-hover:text-[var(--color-primary)] transition-colors">{video.title}</h3>
                            <p className="text-[var(--color-text-muted)] text-sm mb-4">{video.description}</p>

                            <div className="relative aspect-video rounded-xl overflow-hidden border border-white/10 group-hover:border-[var(--color-primary)]/50 transition-colors shadow-lg bg-black/50">
                                {video.type === 'video' ? (
                                    <>
                                        {/* Use video tag as thumbnail, muted, paused at start */}
                                        <video
                                            src={video.src}
                                            className="w-full h-full object-cover opacity-60 group-hover:opacity-80 transition-opacity"
                                            muted
                                            playsInline
                                            onMouseOver={e => e.currentTarget.play()}
                                            onMouseOut={e => { e.currentTarget.pause(); e.currentTarget.currentTime = 0; }}
                                        />
                                        <div className="absolute inset-0 flex items-center justify-center">
                                            <div className="w-16 h-16 rounded-full bg-white/10 backdrop-blur-md border border-white/20 flex items-center justify-center group-hover:scale-110 transition-transform text-white">
                                                <Play className="w-8 h-8 fill-current ml-1" />
                                            </div>
                                        </div>
                                    </>
                                ) : (
                                    <img src={video.src} alt={video.title} className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                                )}
                            </div>
                        </div>
                    </FadeIn>
                ))}
            </div>

            <VideoModal
                isOpen={!!selectedVideo}
                onClose={() => setSelectedVideo(null)}
                videoSrc={selectedVideo?.src || ''}
                title={selectedVideo?.title}
            />
        </>
    );
};
