import React, { useEffect, useState } from 'react';
import {
  SimpleGrid,
  VStack,
  Box,
  Button,
  useDisclosure,
  useToast,
  HStack,
  Text,
  Badge,
  Flex,
  ButtonGroup,
  useColorModeValue
} from '@chakra-ui/react';
import {
  AbnormalityWeightDialog,
  DashboardLayout,
  FileUploadBox,
  GraphPreview,
  type RangeWeight,
} from '.';
import SampleSidebar from '../../components/shared/SampleSidebar';
import ExportDialog from '../../components/shared/ExportDialog';
import { ChangePasswordDialog, useAuth } from '../auth';
import { ParsedCSV, User } from '../../types';
import { useFTIRAnalysis } from '../analysis';

const Dashboard: React.FC = () => {
  const [baselineParsed, setBaselineParsed] = useState<ParsedCSV | undefined>();
  const [baselineFile, setBaselineFile] = useState<File | undefined>();
  const [sampleParsed, setSampleParsed] = useState<ParsedCSV[]>([]);
  const [sampleFiles, setSampleFiles] = useState<FileList | undefined>();
  const [selectedSample, setSelectedSample] = useState<string | undefined>();
  const [abnormalityWeights, setAbnormalityWeights] = useState<RangeWeight[]>([]);
  const [scoringMethod, setScoringMethod] = useState<'area' | 'rmse' | 'hybrid' | 'pearson'>('hybrid'); // Default to hybrid method
  const { isOpen: isExportOpen, onOpen: onExportOpen, onClose: onExportClose } = useDisclosure();
  const { isOpen: isChangePasswordOpen, onOpen: onChangePasswordOpen, onClose: onChangePasswordClose } = useDisclosure();
  const { isOpen: isWeightOpen, onOpen: onWeightOpen, onClose: onWeightClose } = useDisclosure();
  const toast = useToast();
  
  // Get actual user from AuthContext
  const { user: authUser, logout } = useAuth();
  const { calculateScores, scoresResults, clearScores } = useFTIRAnalysis();
  const sampleScores = scoresResults?.scores ?? {};

  useEffect(() => {
    if (!baselineFile || !sampleFiles || sampleFiles.length === 0) {
      clearScores();
      return;
    }
    calculateScores({
      baseline: baselineFile,
      samples: Array.from(sampleFiles),
      scoringMethod,
      zoneWeights: abnormalityWeights,
    }).catch(() => undefined);
  }, [baselineFile, sampleFiles, scoringMethod, abnormalityWeights, calculateScores, clearScores]);

  // User profile menu handlers
  const handleChangePasswordClick = () => {
    onChangePasswordOpen();
  };

  const handleLogoutClick = async () => {
    try {
      await logout();

      toast({
        title: 'Logged Out',
        description: 'You have been successfully logged out.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

      // Redirect to login page
      window.location.href = '/login';
    } catch (error) {
      toast({
        title: 'Logout Failed',
        description: 'An error occurred during logout.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const handleRemoveSample = (filename: string) => {
    const updatedSamples = sampleParsed.filter(s => s.filename !== filename);
    setSampleParsed(updatedSamples);

    // Update selected sample if the removed one was selected
    if (selectedSample === filename) {
      setSelectedSample(updatedSamples.length > 0 ? updatedSamples[0].filename : undefined);
    }

    // Update FileList for backend compatibility
    if (sampleFiles) {
      const dt = new DataTransfer();
      Array.from(sampleFiles)
        .filter(file => file.name !== filename)
        .forEach(file => dt.items.add(file));
      setSampleFiles(dt.files);
    }
  };

  const handleToggleFavorite = (filename: string) => {
    const updatedSamples = sampleParsed.map(sample =>
      sample.filename === filename
        ? { ...sample, isFavorite: !sample.isFavorite }
        : sample
    );
    setSampleParsed(updatedSamples);
  };

  return (
    <DashboardLayout
      navbarTitle="MRG Labs Graphing Dashboard"
      navbarRightContent={
        <Button 
          onClick={onExportOpen}
          variant="outline"
          size="sm"
          colorScheme="gray"
          borderColor="gray.300"
          _hover={{ bg: 'gray.50', borderColor: 'gray.400' }}
          _active={{ bg: 'gray.100' }}
          fontWeight="normal"
        >
          Export
        </Button>
      }
      user={authUser || undefined}
      onChangePasswordClick={handleChangePasswordClick}
      onLogoutClick={handleLogoutClick}
      sidebar={
        <SampleSidebar
          samples={sampleParsed}
          selectedSampleName={selectedSample}
          onSelectSample={setSelectedSample}
          onRemoveSample={handleRemoveSample}
          onToggleFavorite={handleToggleFavorite}
          sampleScores={sampleScores}
        />
      }
    >
      <Box p={6}>
        <VStack align="stretch" spacing={6}>
          <SimpleGrid columns={[1, null, 2]} spacing={4}>
            <FileUploadBox
              label="Baseline CSV"
              multiple={false}
              acceptBaseline
              onFilesParsed={(files, raw) => {
                setBaselineParsed(files[0]);
                setBaselineFile(raw[0]);
              }}
            />
            <FileUploadBox
              label="Sample CSVs"
              multiple
              onFilesParsed={(files: ParsedCSV[], raw: FileList) => {
                setSampleParsed(files);
                setSampleFiles(raw);
                // Update selected sample: keep current if still exists, otherwise pick first available
                if (files.length === 0) {
                  setSelectedSample(undefined);
                } else if (!selectedSample || !files.some(f => f.filename === selectedSample)) {
                  setSelectedSample(files[0].filename);
                }
              }}
            />
          </SimpleGrid>

          {/* Scoring Method Selection and Configure Button */}
          <VStack align="stretch" spacing={3} w="100%">
            <Flex justify="space-between" align="center" w="100%">
              <HStack spacing={4}>
                <Text fontSize="md" fontWeight="semibold" color={useColorModeValue('gray.700', 'gray.200')}>
                  Scoring Method:
                </Text>
                <ButtonGroup size="sm" isAttached variant="outline">
                  <Button
                    onClick={() => setScoringMethod('rmse')}
                    colorScheme={scoringMethod === 'rmse' ? 'blue' : 'gray'}
                    bg={scoringMethod === 'rmse' ? 'blue.500' : useColorModeValue('white', 'gray.700')}
                    color={scoringMethod === 'rmse' ? 'white' : useColorModeValue('gray.700', 'gray.200')}
                    _hover={{
                      bg: scoringMethod === 'rmse' ? 'blue.600' : useColorModeValue('gray.100', 'gray.600')
                    }}
                    fontWeight={scoringMethod === 'rmse' ? 'bold' : 'normal'}
                  >
                    RMSE Deviation
                  </Button>
                  <Button
                    onClick={() => setScoringMethod('hybrid')}
                    colorScheme={scoringMethod === 'hybrid' ? 'blue' : 'gray'}
                    bg={scoringMethod === 'hybrid' ? 'blue.500' : useColorModeValue('white', 'gray.700')}
                    color={scoringMethod === 'hybrid' ? 'white' : useColorModeValue('gray.700', 'gray.200')}
                    _hover={{
                      bg: scoringMethod === 'hybrid' ? 'blue.600' : useColorModeValue('gray.100', 'gray.600')
                    }}
                    fontWeight={scoringMethod === 'hybrid' ? 'bold' : 'normal'}
                  >
                    Hybrid (RMSE + Shape)
                  </Button>
                  <Button
                    onClick={() => setScoringMethod('pearson')}
                    colorScheme={scoringMethod === 'pearson' ? 'blue' : 'gray'}
                    bg={scoringMethod === 'pearson' ? 'blue.500' : useColorModeValue('white', 'gray.700')}
                    color={scoringMethod === 'pearson' ? 'white' : useColorModeValue('gray.700', 'gray.200')}
                    _hover={{
                      bg: scoringMethod === 'pearson' ? 'blue.600' : useColorModeValue('gray.100', 'gray.600')
                    }}
                    fontWeight={scoringMethod === 'pearson' ? 'bold' : 'normal'}
                  >
                    Pearson Correlation
                  </Button>
                  <Button
                    onClick={() => setScoringMethod('area')}
                    colorScheme={scoringMethod === 'area' ? 'blue' : 'gray'}
                    bg={scoringMethod === 'area' ? 'blue.500' : useColorModeValue('white', 'gray.700')}
                    color={scoringMethod === 'area' ? 'white' : useColorModeValue('gray.700', 'gray.200')}
                    _hover={{
                      bg: scoringMethod === 'area' ? 'blue.600' : useColorModeValue('gray.100', 'gray.600')
                    }}
                    fontWeight={scoringMethod === 'area' ? 'bold' : 'normal'}
                  >
                    Area Difference
                  </Button>
                </ButtonGroup>
              </HStack>
              <Button
                colorScheme="purple"
                variant="outline"
                size="md"
                onClick={onWeightOpen}
              >
                Configure Abnormality Weights
              </Button>
            </Flex>

            {/* Selected Sample Info */}
            {selectedSample && sampleScores[selectedSample] !== undefined && (
              <HStack>
                <Text fontSize="md" fontWeight="medium" color={useColorModeValue('gray.700', 'gray.300')}>
                  Selected Sample:
                </Text>
                <Text fontSize="md" fontWeight="bold" color={useColorModeValue('blue.700', 'blue.300')} maxW="300px" noOfLines={1}>
                  {selectedSample?.replace('.csv', '') || ''}
                </Text>
                <Badge
                  colorScheme={
                    sampleScores[selectedSample] >= 90 ? 'green' : 
                    sampleScores[selectedSample] >= 70 ? 'yellow' : 'red'
                  }
                  size="md"
                  fontSize="sm"
                  fontWeight="bold"
                  px={3}
                  py={1}
                >
                  Score: {Math.round(sampleScores[selectedSample])}
                </Badge>
              </HStack>
            )}
          </VStack>

          <GraphPreview
            baseline={baselineParsed}
            samples={sampleParsed}
            selectedSampleName={selectedSample}
            onSelectSample={setSelectedSample}
            abnormalityWeights={abnormalityWeights}
            deviationData={scoresResults?.deviationData}
          />
        </VStack>
      </Box>

      {/* Export Dialog */}
      <ExportDialog
        isOpen={isExportOpen}
        onClose={onExportClose}
        baseline={baselineParsed}
        samples={sampleParsed}
      />

      {/* Change Password Dialog */}
      <ChangePasswordDialog
        isOpen={isChangePasswordOpen}
        onClose={onChangePasswordClose}
      />

      {/* Abnormality Weight Configuration Dialog */}
      <AbnormalityWeightDialog
        isOpen={isWeightOpen}
        onClose={onWeightClose}
        onSave={(weights) => {
          setAbnormalityWeights(weights);
          localStorage.setItem('abnormalityWeights', JSON.stringify(weights));
          toast({
            title: 'Weights Saved',
            description: 'Abnormality calculation weights have been configured',
            status: 'success',
            duration: 3000,
            isClosable: true,
          });
        }}
        initialWeights={abnormalityWeights}
      />
    </DashboardLayout>
  );
};

export default Dashboard;
