import React, { useRef } from 'react';
import { Box, VStack, Text, HStack, Button, Badge, useColorModeValue } from '@chakra-ui/react';
import type { RangeWeight } from '../../types';

interface Props {
  x: number[];
  deviation: number[];
  selectedSampleName?: string;
  showGrid?: boolean;
  onResetZoom?: () => void;
  resetKey?: number;
  abnormalityWeights?: RangeWeight[];
}

const DeviationHeatBar = React.forwardRef<any, Props>(({ 
  x, 
  deviation, 
  selectedSampleName,
  showGrid = true,
  onResetZoom,
  resetKey = 0,
  abnormalityWeights = []
}, ref) => {
  const hasData = x.length > 0 && deviation.length > 0;
  
  const handleResetZoom = () => {
    if (onResetZoom) {
      onResetZoom();
    }
  };

  // Calculate the maximum deviation for normalization
  const maxDeviation = hasData ? Math.max(...deviation) : 1;
  const minDeviation = hasData ? Math.min(...deviation) : 0;
  
  // Function to get color based on deviation value
  const getColor = (value: number): string => {
    if (maxDeviation === 0) return 'rgb(0, 255, 0)'; // All green if no deviation
    
    // Normalize the value to 0-1 range
    const normalized = value / maxDeviation;
    
    if (normalized <= 0.33) {
      // Green to Yellow (0-33%)
      const ratio = normalized / 0.33;
      const red = Math.round(255 * ratio);
      const green = 255;
      return `rgb(${red}, ${green}, 0)`;
    } else if (normalized <= 0.66) {
      // Yellow to Orange (33-66%)
      const ratio = (normalized - 0.33) / 0.33;
      const red = 255;
      const green = Math.round(255 * (1 - ratio * 0.5)); // Fade to 127
      return `rgb(${red}, ${green}, 0)`;
    } else {
      // Orange to Red (66-100%)
      const ratio = (normalized - 0.66) / 0.34;
      const red = 255;
      const green = Math.round(127 * (1 - ratio)); // Fade from 127 to 0
      return `rgb(${red}, ${green}, 0)`;
    }
  };

  // Create gradient segments with better hover interaction
  const createGradientSegments = () => {
    if (!hasData) return [];
    
    const segments = [];
    const totalWidth = 100; // Percentage
    const segmentWidth = totalWidth / x.length;
    
    for (let i = 0; i < x.length; i++) {
      const color = getColor(deviation[i]);
      const left = i * segmentWidth;
      const deviationPercent = ((deviation[i] / maxDeviation) * 100).toFixed(1);
      
      segments.push(
        <Box
          key={i}
          position="absolute"
          left={`${left}%`}
          width={`${segmentWidth}%`}
          height="100%"
          backgroundColor={color}
          title={`${Math.round(x[i])} cm⁻¹\nDeviation: ${deviation[i].toFixed(4)} (${deviationPercent}% of max)`}
          cursor="crosshair"
          transition="all 0.15s ease"
          _hover={{
            transform: 'scaleY(1.15)',
            zIndex: 10,
            boxShadow: '0 0 8px rgba(0,0,0,0.3)',
            filter: 'brightness(1.2)'
          }}
        />
      );
    }
    
    return segments;
  };

  // Create wavelength markers - matching main graph ticks
  const createWavelengthMarkers = () => {
    if (!hasData) return [];
    
    const markers: JSX.Element[] = [];
    const minX = Math.min(...x);
    const maxX = Math.max(...x);
    const range = maxX - minX;
    
    // Use standard FTIR ticks that match the main graph
    const customXTicks = [4000, 3500, 3000, 2500, 2000, 1750, 1500, 1250, 1000, 750, 550];
    
    customXTicks.forEach((wavelength) => {
      if (wavelength >= minX && wavelength <= maxX) {
        const position = ((maxX - wavelength) / range) * 100; // Reverse for IR
        
        markers.push(
          <Box
            key={wavelength}
            position="absolute"
            left={`${position}%`}
            transform="translateX(-50%)"
          >
            {/* Vertical guide line */}
            <Box
              position="absolute"
              bottom="20px"
              left="50%"
              width="1px"
              height="80px"
              bg={useColorModeValue('gray.400', 'gray.600')}
              opacity={0.3}
            />
            {/* Label */}
            <Text
              fontSize="xs"
              fontWeight="medium"
              color={useColorModeValue('gray.700', 'gray.300')}
              whiteSpace="nowrap"
              bg={bgCard}
              px={1}
              borderRadius="sm"
            >
              {wavelength}
            </Text>
          </Box>
        );
      }
    });
    
    return markers;
  };

  // Create color scale legend
  const createColorScale = () => {
    const steps = 20;
    const segments = [];
    
    for (let i = 0; i < steps; i++) {
      const value = (i / (steps - 1)) * maxDeviation;
      const color = getColor(value);
      const left = (i / (steps - 1)) * 100;
      
      segments.push(
        <Box
          key={i}
          position="absolute"
          left={`${left}%`}
          width={`${100/steps}%`}
          height="100%"
          backgroundColor={color}
        />
      );
    }
    
    return segments;
  };

  // Create weight range indicators
  const createWeightRanges = () => {
    if (!abnormalityWeights || abnormalityWeights.length === 0) return null;

    const minX = Math.min(...x);
    const maxX = Math.max(...x);
    const range = maxX - minX;
    
    return abnormalityWeights.map((weightRange, index) => {
      // Calculate position and width for this range
      const rangeStart = Math.max(weightRange.min, minX);
      const rangeEnd = Math.min(weightRange.max, maxX);
      
      if (rangeStart >= rangeEnd) return null;
      
      // Convert wavelengths to percentages (reverse for IR)
      const startPercent = ((maxX - rangeEnd) / range) * 100;
      const endPercent = ((maxX - rangeStart) / range) * 100;
      const widthPercent = endPercent - startPercent;
      
      // Color based on weight intensity
      const weightIntensity = weightRange.weight / 100;
      const alpha = 0.2 + (weightIntensity * 0.3); // More weight = more visible
      
      const colors = {
        'range_evaporation': `rgba(255, 99, 71, ${alpha})`, // Tomato
        'range_other': `rgba(255, 165, 0, ${alpha})`, // Orange  
        'range_oxidation': `rgba(255, 20, 147, ${alpha})` // Deep pink
      };
      
      const color = colors[weightRange.key as keyof typeof colors] || `rgba(128, 128, 128, ${alpha})`;
      
      return (
        <Box
          key={index}
          position="absolute"
          left={`${startPercent}%`}
          width={`${widthPercent}%`}
          height="100%"
          backgroundColor={color}
          borderLeft={index > 0 ? "1px solid rgba(0,0,0,0.2)" : undefined}
          title={`${weightRange.label}: ${weightRange.weight}% weight`}
        />
      );
    }).filter(Boolean);
  };

  const bgCard = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.300', 'gray.600');
  const textPrimary = useColorModeValue('gray.800', 'gray.100');
  const textSecondary = useColorModeValue('gray.600', 'gray.400');
  const legendGreenBg = useColorModeValue('green.100', 'green.900');
  const legendGreenText = useColorModeValue('green.800', 'green.200');
  const legendYellowBg = useColorModeValue('yellow.100', 'yellow.900');
  const legendYellowText = useColorModeValue('yellow.800', 'yellow.200');
  const legendRedBg = useColorModeValue('red.100', 'red.900');
  const legendRedText = useColorModeValue('red.800', 'red.200');

  return (
    <Box w="100%" bg={bgCard} p={4} borderWidth="1px" rounded="md" shadow="sm">
      <VStack align="start" spacing={4}>
        <Box w="100%" pb={2} borderBottom="2px solid" borderColor={borderColor}>
          <HStack justify="space-between" align="center">
            <VStack align="start" spacing={1}>
              <Text fontWeight="bold" fontSize="lg" color={textPrimary}>
                Spectral Deviation Heat Map
              </Text>
              <Text fontSize="xs" color={textSecondary}>
                Visual representation of deviation intensity across the spectrum
              </Text>
            </VStack>
            <HStack spacing={2}>
              <Box textAlign="center" px={3} py={1} bg={legendGreenBg} borderRadius="md">
                <Text fontSize="xs" fontWeight="bold" color={legendGreenText}>Good</Text>
              </Box>
              <Box textAlign="center" px={3} py={1} bg={legendYellowBg} borderRadius="md">
                <Text fontSize="xs" fontWeight="bold" color={legendYellowText}>Monitor</Text>
              </Box>
              <Box textAlign="center" px={3} py={1} bg={legendRedBg} borderRadius="md">
                <Text fontSize="xs" fontWeight="bold" color={legendRedText}>Critical</Text>
              </Box>
            </HStack>
          </HStack>
        </Box>

        {hasData ? (
          <VStack w="100%" spacing={4}>
            {/* Main heat bar with improved visuals */}
            <Box w="100%" position="relative">
              <HStack justify="space-between" mb={3}>
                <Text fontSize="md" fontWeight="bold" color={textPrimary}>
                  Deviation Intensity Map
                </Text>
                {selectedSampleName && (
                  <Badge colorScheme="blue" fontSize="xs" px={2} py={1}>
                    {selectedSampleName.replace(/\.csv$/i, '')}
                  </Badge>
                )}
              </HStack>
              
              <Box position="relative" w="100%">
                {/* Wavelength axis labels above */}
                <Box position="relative" h="25px" mb={1}>
                  {createWavelengthMarkers()}
                </Box>
                
                {/* Main heat bar with better height and styling */}
                <Box
                  position="relative"
                  w="100%"
                  h="80px"
                  border="2px solid"
                  borderColor={useColorModeValue('gray.400', 'gray.600')}
                  borderRadius="lg"
                  overflow="visible"
                  bg={bgCard}
                  boxShadow="md"
                >
                  {/* Weight ranges background */}
                  {createWeightRanges()}
                  {/* Deviation gradient overlay */}
                  {createGradientSegments()}
                </Box>
                
                {/* Axis label */}
                <Text fontSize="sm" fontWeight="semibold" color={useColorModeValue('gray.700', 'gray.300')} textAlign="center" mt={2}>
                  Wavenumber (cm⁻¹)
                </Text>
              </Box>
            </Box>

            {/* Statistics Cards */}
            <HStack w="100%" spacing={4}>
              <Box 
                flex={1} 
                p={3} 
                bg={useColorModeValue('red.50', 'red.900')}
                borderRadius="lg" 
                borderWidth="1px" 
                borderColor={useColorModeValue('red.200', 'red.700')}
              >
                <Text fontSize="xs" fontWeight="medium" color={useColorModeValue('red.700', 'red.200')} mb={1}>
                  Max Deviation
                </Text>
                <Text fontSize="lg" fontWeight="bold" color={useColorModeValue('red.600', 'red.300')}>
                  {maxDeviation.toFixed(4)}
                </Text>
              </Box>
              <Box 
                flex={1} 
                p={3} 
                bg={useColorModeValue('orange.50', 'orange.900')}
                borderRadius="lg" 
                borderWidth="1px" 
                borderColor={useColorModeValue('orange.200', 'orange.700')}
              >
                <Text fontSize="xs" fontWeight="medium" color={useColorModeValue('orange.700', 'orange.200')} mb={1}>
                  Avg Deviation
                </Text>
                <Text fontSize="lg" fontWeight="bold" color={useColorModeValue('orange.600', 'orange.300')}>
                  {(deviation.reduce((a, b) => a + b, 0) / deviation.length).toFixed(4)}
                </Text>
              </Box>
              <Box 
                flex={1} 
                p={3} 
                bg={useColorModeValue('green.50', 'green.900')}
                borderRadius="lg" 
                borderWidth="1px" 
                borderColor={useColorModeValue('green.200', 'green.700')}
              >
                <Text fontSize="xs" fontWeight="medium" color={useColorModeValue('green.700', 'green.200')} mb={1}>
                  Min Deviation
                </Text>
                <Text fontSize="lg" fontWeight="bold" color={useColorModeValue('green.600', 'green.300')}>
                  {minDeviation.toFixed(4)}
                </Text>
              </Box>
            </HStack>

            {/* Color scale legend */}
            <Box w="100%" p={3} bg={useColorModeValue('gray.50', 'gray.700')} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
              <Text fontSize="sm" fontWeight="bold" mb={2} color={textPrimary}>
                Deviation Color Scale
              </Text>
              <VStack spacing={2} align="stretch">
                <HStack spacing={2}>
                  <Box
                    position="relative"
                    flex={1}
                    h="30px"
                    border="2px solid"
                    borderColor={borderColor}
                    borderRadius="md"
                    overflow="hidden"
                    boxShadow="sm"
                  >
                    {createColorScale()}
                  </Box>
                </HStack>
                <HStack justify="space-between">
                  <HStack spacing={1}>
                    <Box w="12px" h="12px" bg="rgb(0, 255, 0)" borderRadius="sm" />
                    <Text fontSize="xs" fontWeight="medium" color={useColorModeValue('gray.700', 'gray.300')}>
                      Low (0.000)
                    </Text>
                  </HStack>
                  <HStack spacing={1}>
                    <Box w="12px" h="12px" bg="rgb(255, 255, 0)" borderRadius="sm" />
                    <Text fontSize="xs" fontWeight="medium" color={useColorModeValue('gray.700', 'gray.300')}>
                      Medium
                    </Text>
                  </HStack>
                  <HStack spacing={1}>
                    <Box w="12px" h="12px" bg="rgb(255, 0, 0)" borderRadius="sm" />
                    <Text fontSize="xs" fontWeight="medium" color={useColorModeValue('gray.700', 'gray.300')}>
                      High ({maxDeviation.toFixed(3)})
                    </Text>
                  </HStack>
                </HStack>
              </VStack>
            </Box>

            {/* Weight Ranges Legend */}
            {abnormalityWeights && abnormalityWeights.length > 0 && (
              <Box w="100%" p={4} bg={useColorModeValue('purple.50', 'purple.900')} borderRadius="lg" borderWidth="2px" borderColor={useColorModeValue('purple.200', 'purple.700')}>
                <Text fontSize="sm" fontWeight="bold" mb={3} color={useColorModeValue('purple.900', 'purple.100')}>
                  ⚖️ Applied Weight Ranges
                </Text>
                <VStack spacing={2} align="stretch">
                  {abnormalityWeights.map((range, index) => {
                    const colors = {
                      'range_evaporation': 'rgba(255, 99, 71, 0.6)',
                      'range_other': 'rgba(255, 165, 0, 0.6)', 
                      'range_oxidation': 'rgba(255, 20, 147, 0.6)'
                    };
                    const color = colors[range.key as keyof typeof colors] || 'rgba(128, 128, 128, 0.6)';
                    
                    return (
                      <HStack 
                        key={index} 
                        spacing={3} 
                        p={2} 
                        bg={bgCard}
                        borderRadius="md"
                        borderWidth="1px"
                        borderColor={useColorModeValue('purple.100', 'purple.800')}
                      >
                        <Box
                          w="24px"
                          h="24px"
                          backgroundColor={color}
                          border="2px solid"
                          borderColor={useColorModeValue('gray.400', 'gray.600')}
                          borderRadius="md"
                          flexShrink={0}
                        />
                        <VStack align="start" spacing={0} flex={1}>
                          <Text fontSize="xs" fontWeight="bold" color={textPrimary}>
                            {range.label}
                          </Text>
                          <Text fontSize="xs" color={textSecondary}>
                            {range.min} - {range.max} cm⁻¹
                          </Text>
                        </VStack>
                        <Badge colorScheme="purple" fontSize="xs" px={2} py={1}>
                          {range.weight}% weight
                        </Badge>
                      </HStack>
                    );
                  })}
                </VStack>
                <Text fontSize="xs" color={useColorModeValue('purple.700', 'purple.300')} mt={2} fontStyle="italic">
                  💡 Background colors on heat map show these weighted regions
                </Text>
              </Box>
            )}
          </VStack>
        ) : (
          <Text fontSize="sm" color={textSecondary}>
            Upload baseline and multiple samples to see oxidation heat map.
          </Text>
        )}

        {/* Interactive guidance */}
        {hasData && (
          <Box w="100%" p={4} bg={useColorModeValue('blue.50', 'blue.900')} rounded="lg" borderWidth="2px" borderColor={useColorModeValue('blue.300', 'blue.700')}>
            <HStack spacing={2} mb={2}>
              <Text fontSize="lg">💡</Text>
              <Text fontSize="sm" fontWeight="bold" color={useColorModeValue('blue.900', 'blue.100')}>
                How to Read This Map
              </Text>
            </HStack>
            <VStack align="start" spacing={1}>
              <HStack spacing={2}>
                <Box w="8px" h="8px" bg="rgb(0, 255, 0)" borderRadius="full" />
                <Text fontSize="xs" color={useColorModeValue('blue.800', 'blue.200')}>
                  <strong>Green zones:</strong> Stable grease, minimal deviation from baseline
                </Text>
              </HStack>
              <HStack spacing={2}>
                <Box w="8px" h="8px" bg="rgb(255, 255, 0)" borderRadius="full" />
                <Text fontSize="xs" color={useColorModeValue('blue.800', 'blue.200')}>
                  <strong>Yellow zones:</strong> Moderate changes, monitor for trending
                </Text>
              </HStack>
              <HStack spacing={2}>
                <Box w="8px" h="8px" bg="rgb(255, 0, 0)" borderRadius="full" />
                <Text fontSize="xs" color={useColorModeValue('blue.800', 'blue.200')}>
                  <strong>Red zones:</strong> Critical oxidation/contamination detected
                </Text>
              </HStack>
              <Text fontSize="xs" color={useColorModeValue('blue.700', 'blue.300')} mt={2} fontStyle="italic">
                💡 Hover over any section to see exact wavenumber and deviation values
              </Text>
            </VStack>
          </Box>
        )}
      </VStack>
    </Box>
  );
});

DeviationHeatBar.displayName = 'DeviationHeatBar';

export default DeviationHeatBar;
