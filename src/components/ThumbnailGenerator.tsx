import { useRef, useState } from 'react';
import { Image as ImageIcon, Save } from 'lucide-react';
import toast from 'react-hot-toast';

interface ThumbnailGeneratorProps {
  /**
   * URL of the AI-generated thumbnail frame.
   * If null/undefined, the component shows an informational message.
   */
  thumbnailUrl: string | null;

  /** Optional brand label shown on the thumbnail badge (default: "SnipX"). */
  brandLabel?: string;
}

const ThumbnailGenerator = ({ thumbnailUrl, brandLabel = 'SnipX' }: ThumbnailGeneratorProps) => {
  const [thumbnailTitle, setThumbnailTitle] = useState('');
  const [thumbnailSubtitle, setThumbnailSubtitle] = useState('');
  const [brandColor, setBrandColor] = useState('#7c3aed');
  const thumbnailCanvasRef = useRef<HTMLCanvasElement | null>(null);

  // Debug logging
  console.log('ThumbnailGenerator rendered:', { thumbnailUrl, hasThumbnail: !!thumbnailUrl });

  const handleDownload = async () => {
    if (!thumbnailUrl) {
      toast.error('No thumbnail generated yet');
      return;
    }

    const canvas = thumbnailCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = thumbnailUrl;

    try {
      await new Promise<void>((resolve, reject) => {
        img.onload = () => resolve();
        img.onerror = () => reject(new Error('Failed to load thumbnail image'));
      });
    } catch (error) {
      console.error(error);
      toast.error('Unable to load thumbnail for download');
      return;
    }

    const width = 1280;
    const height = 720;
    canvas.width = width;
    canvas.height = height;

    ctx.drawImage(img, 0, 0, width, height);

    // Dark band at bottom
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(0, height - 220, width, 220);

    // Brand strip
    ctx.fillStyle = brandColor || '#7c3aed';
    ctx.fillRect(0, height - 220, 12, 220);

    ctx.fillStyle = '#ffffff';
    ctx.textBaseline = 'top';

    const wrapText = (
      context: CanvasRenderingContext2D,
      text: string,
      x: number,
      y: number,
      maxWidth: number,
      lineHeight: number
    ) => {
      const words = text.split(' ');
      let line = '';
      for (let n = 0; n < words.length; n++) {
        const testLine = line + words[n] + ' ';
        const metrics = context.measureText(testLine);
        const testWidth = metrics.width;
        if (testWidth > maxWidth && n > 0) {
          context.fillText(line, x, y);
          line = words[n] + ' ';
          y += lineHeight;
        } else {
          line = testLine;
        }
      }
      context.fillText(line, x, y);
    };

    const title = thumbnailTitle || 'Your video title';
    const subtitle = thumbnailSubtitle || 'Engaging hook or description goes here';

    ctx.font = 'bold 56px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    wrapText(ctx, title, 40, height - 195, width - 80, 64);

    ctx.font = '28px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    wrapText(ctx, subtitle, 40, height - 95, width - 80, 36);

    canvas.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'snipx-thumbnail.png';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    }, 'image/png');
  };

  return (
    <>
      <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <ImageIcon className="text-purple-600 mr-3" size={20} />
            <div>
              <h4 className="text-sm font-medium text-gray-900">Thumbnail Generation</h4>
              <p className="text-xs text-gray-500">AI-picked frame with custom branding</p>
            </div>
          </div>
        </div>

        {thumbnailUrl ? (
          <div className="mt-3 space-y-3">
            <div className="relative rounded-md overflow-hidden border border-gray-200">
              <img 
                src={thumbnailUrl}
                alt="Generated thumbnail"
                className="w-full h-40 object-cover"
                onLoad={() => console.log('✅ Thumbnail image loaded successfully')}
                onError={(e) => {
                  console.error('❌ Thumbnail image failed to load:', e);
                  console.error('Failed URL:', thumbnailUrl);
                }}
              />
              <div className="absolute inset-0 flex flex-col justify-end p-3 pointer-events-none">
                <span 
                  className="inline-block px-2 py-1 text-xs font-semibold text-white rounded" 
                  style={{ backgroundColor: brandColor }}
                >
                  {brandLabel}
                </span>
                <span className="mt-2 text-sm font-bold text-white drop-shadow-md line-clamp-2">
                  {thumbnailTitle || 'Your video title'}
                </span>
                <span className="text-xs text-gray-200 drop-shadow-md line-clamp-1">
                  {thumbnailSubtitle || 'Engaging hook or description goes here'}
                </span>
              </div>
            </div>

            <div className="space-y-2">
              <div>
                <label className="block text-xs text-gray-600 mb-1">Title text</label>
                <input
                  type="text"
                  value={thumbnailTitle}
                  onChange={(e) => setThumbnailTitle(e.target.value)}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 text-sm"
                  placeholder="e.g. 5 Editing Tricks to Boost Your Reels"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Subtitle text</label>
                <input
                  type="text"
                  value={thumbnailSubtitle}
                  onChange={(e) => setThumbnailSubtitle(e.target.value)}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 text-sm"
                  placeholder="e.g. Edit faster with AI-powered tools"
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-600">Brand color</span>
                <input
                  type="color"
                  value={brandColor}
                  onChange={(e) => setBrandColor(e.target.value)}
                  className="w-10 h-6 p-0 border border-gray-300 rounded cursor-pointer"
                />
              </div>
            </div>

            <button
              type="button"
              onClick={handleDownload}
              className="w-full mt-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-md text-sm font-medium flex items-center justify-center transition-colors"
            >
              <Save className="mr-2" size={16} />
              Download Thumbnail
            </button>
          </div>
        ) : (
          <p className="mt-3 text-xs text-gray-500">
            No thumbnail available yet. Process your video to generate one.
          </p>
        )}
      </div>

      {/* Hidden canvas for thumbnail download rendering */}
      <canvas ref={thumbnailCanvasRef} className="hidden" />
    </>
  );
};

export default ThumbnailGenerator;
